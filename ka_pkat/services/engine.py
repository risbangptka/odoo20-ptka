"""Mesin pemeriksaan anggaran (SRS 4.3, BRD BR-07 / BR-12).

Sengaja ditulis sebagai Python murni TANPA impor Odoo, supaya aturan keputusan
dapat diuji cepat dengan unittest biasa (lihat tests/test_engine.py).
Lapisan Odoo (controller/service) bertugas:
  1. menerjemahkan baris dokumen menjadi struktur di bawah,
  2. mengunci baris pkat.pocket / pkat.project (FOR UPDATE),
  3. memanggil check_document(),
  4. menulis buku serapan + log sesuai hasilnya.
"""

KIND_SPM = 'SPM'
KIND_PO = 'PO'
KIND_REAL = 'REALISASI'

OK = 'OK'
PASS_UNCONTROLLED = 'PASS_UNCONTROLLED'
WARN_ACCOUNT_OVER = 'WARN_ACCOUNT_OVER'
WARN_POCKET_OVER = 'WARN_POCKET_OVER'
REJECT_NO_BUDGET = 'REJECT_NO_BUDGET'
REJECT_POCKET_OVER = 'REJECT_POCKET_OVER'
REJECT_PROJECT_OVER = 'REJECT_PROJECT_OVER'
REJECT_PROJECT_CLOSED = 'REJECT_PROJECT_CLOSED'
REJECT_MANUAL_LOCK = 'REJECT_MANUAL_LOCK'

_SEVERITY = {'ok': 0, 'warn': 1, 'reject': 2}


def status_of(code):
    if code.startswith('REJECT'):
        return 'reject'
    if code.startswith('WARN'):
        return 'warn'
    return 'ok'


class Position(object):
    """Posisi satu objek anggaran (perkiraan, kantung, atau proyek) untuk SATU ukuran:
    serapan (cek SPM/PO) atau realisasi (cek REALISASI).

    key    : pengenal unik (dipakai untuk akumulasi antar baris dalam satu dokumen)
    budget : anggaran berlaku setahun
    plan   : 12 rencana bulanan (Jan..Des)
    used   : 12 nilai terpakai per bulan (Jan..Des)
    """

    def __init__(self, key, budget, plan=None, used=None, name=None):
        self.key = key
        self.name = name or str(key)
        self.budget = float(budget or 0.0)
        self.plan = list(plan) if plan else [self.budget / 12.0] * 12
        self.used = list(used) if used else [0.0] * 12


def window(basis, month, pos):
    """(batas, terpakai) menurut dasar penguncian. month = bulan dokumen (1..12).

    yearly : batas = anggaran setahun      ; terpakai = kumulatif setahun
    ytd    : batas = rencana bulan 1..M    ; terpakai = kumulatif s.d. bulan M
    mtd    : batas = rencana bulan M       ; terpakai = dalam bulan M
    """
    if basis == 'ytd':
        return sum(pos.plan[:month]), sum(pos.used[:month])
    if basis == 'mtd':
        return pos.plan[month - 1], pos.used[month - 1]
    return pos.budget, sum(pos.used)


def _over(limit, used, amount):
    # tepat 100% diperbolehkan; bandingkan pada 2 desimal
    return round(used + amount, 2) > round(limit, 2)


def check_document(kind, lines, basis='yearly'):
    """Periksa satu dokumen.

    lines: list of dict, tiap baris:
        ref            : pengenal baris
        amount         : nilai baris (rupiah)
        month          : bulan tanggal dokumen (1..12)
        controlled     : False bila perkiraan tidak dikendalikan (pendapatan, Tebu SPT, kunci mati)
        account        : Position perkiraan, atau None bila tidak dianggarkan
        pocket         : Position kantung, atau None
        manual_lock    : True bila kantung dikunci manual
        project        : Position proyek (opsional)
        project_closed : True bila proyek sudah ditutup

    Hasil: dict(status, code, lines=[...]). Bila ada satu baris reject, seluruh
    dokumen reject (pemanggil tidak boleh mencatat serapan apa pun).
    """
    extra = {}  # akumulasi nilai baris sebelumnya dalam dokumen ini, per key posisi
    results = []
    for line in lines:
        amount = float(line.get('amount') or 0.0)
        month = int(line.get('month') or 1)
        res = {'ref': line.get('ref'), 'code': OK, 'limit': None, 'used': None, 'after': None}

        if not line.get('controlled', True):
            res['code'] = PASS_UNCONTROLLED
            results.append(res)
            continue

        project = line.get('project')
        account = line.get('account')
        pocket = line.get('pocket')
        code = OK

        # --- proyek / Nomor Investasi ---
        if project is not None:
            if line.get('project_closed'):
                code = REJECT_PROJECT_CLOSED
            else:
                limit, used = project.budget, sum(project.used)
                used += extra.get(('project', project.key), 0.0)
                res.update(limit=limit, used=used, after=used + amount)
                if _over(limit, used, amount):
                    code = WARN_POCKET_OVER if kind == KIND_SPM else REJECT_PROJECT_OVER

        # --- perkiraan biaya + kantung (juga untuk PO PLB yang membawa perkiraan) ---
        if status_of(code) != 'reject' and (account is not None or project is None):
            if account is None:
                code = REJECT_NO_BUDGET
            elif pocket is not None:
                if line.get('manual_lock') and kind != KIND_SPM:
                    code = REJECT_MANUAL_LOCK
                else:
                    limit, used = window(basis, month, pocket)
                    used += extra.get(('pocket', pocket.key), 0.0)
                    res.update(limit=limit, used=used, after=used + amount)
                    if _over(limit, used, amount):
                        code = WARN_POCKET_OVER if kind == KIND_SPM else REJECT_POCKET_OVER
                    elif code == OK:
                        a_limit, a_used = window(basis, month, account)
                        a_used += extra.get(('account', account.key), 0.0)
                        if _over(a_limit, a_used, amount):
                            code = WARN_ACCOUNT_OVER

        res['code'] = code
        results.append(res)
        if status_of(code) != 'reject':
            for prefix, pos in (('project', project), ('pocket', pocket), ('account', account)):
                if pos is not None:
                    extra[(prefix, pos.key)] = extra.get((prefix, pos.key), 0.0) + amount

    worst = max(results, key=lambda r: _SEVERITY[status_of(r['code'])]) if results else None
    return {
        'status': status_of(worst['code']) if worst else 'ok',
        'code': worst['code'] if worst else OK,
        'lines': results,
    }


def ews_color(pct, yellow=75.0, red=100.0):
    """SRS FS-EW-01."""
    if pct > red:
        return 'red'
    if pct > yellow:
        return 'yellow'
    return 'green'
