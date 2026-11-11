"""FS-PK-01: impor PKAT dari Excel berformat baku (template dapat diunduh).

Satu baris per perkiraan: tahun, kode stasiun, nomor perkiraan, 4 komponen
(barang, non-barang, tenaga kerja, proyek), rencana Januari-Desember.
Hanya grup pkat_anggaran_kd.
"""
import io
from collections import OrderedDict

from odoo import _, fields, models
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.tools import BinaryBytes, float_compare, formatLang

MONTH_LABELS = ['Jan', 'Feb', 'Mar', 'Apr', 'Mei', 'Jun', 'Jul', 'Agu', 'Sep', 'Okt', 'Nov', 'Des']
COMPONENTS = [
    ('amount_goods', 'Barang'),
    ('amount_nongoods', 'Non Barang'),
    ('amount_wage', 'Tenaga Kerja'),
    ('amount_project', 'Proyek'),
]
HEADERS = ['Tahun', 'Kode Stasiun', 'No. Perkiraan'] + [label for _f, label in COMPONENTS] + MONTH_LABELS
N_COLS = len(HEADERS)  # 19
MAX_ERRORS_SHOWN = 30


def _cell_text(value):
    """Kode dari sel Excel: angka 25.0 -> '25', teks dipangkas."""
    if value is None:
        return ''
    if isinstance(value, float) and value.is_integer():
        value = int(value)
    return str(value).strip()


class PkatBudgetImport(models.TransientModel):
    _name = 'pkat.budget.import'
    _description = 'Impor PKAT dari Excel'

    company_id = fields.Many2one('res.company', string='Unit/PG', required=True,
                                 default=lambda self: self.env.company)
    file = fields.Binary('Berkas Excel (.xlsx)', attachment=False)
    filename = fields.Char('Nama Berkas')
    template_file = fields.Binary('Template', attachment=False, readonly=True)
    state = fields.Selection([('draft', 'Unggah'), ('done', 'Hasil')], default='draft')
    result_message = fields.Text('Hasil Impor', readonly=True)
    imported_count = fields.Integer('Baris Diimpor', readonly=True)
    failed_count = fields.Integer('Baris Gagal', readonly=True)
    error_file = fields.Binary('Baris Gagal (.xlsx)', attachment=False, readonly=True)
    error_filename = fields.Char('Nama Berkas Baris Gagal', readonly=True)

    # ------------------------------------------------------------------ hak
    def _check_group(self):
        if not self.env.su and not self.env.user.has_group('ka_pkat.group_pkat_anggaran_kd'):
            raise AccessError(_("Impor PKAT hanya untuk Bagian Anggaran Kantor Direksi."))

    def _reopen(self):
        return {
            'type': 'ir.actions.act_window',
            'res_model': self._name,
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        }

    # ------------------------------------------------------------- template
    def _build_template(self):
        import xlsxwriter  # pustaka bawaan image Odoo
        buf = io.BytesIO()
        book = xlsxwriter.Workbook(buf, {'in_memory': True})
        head = book.add_format({'bold': True, 'bg_color': '#DDDDDD', 'border': 1})
        text = book.add_format({'num_format': '@'})
        money = book.add_format({'num_format': '#,##0.00'})
        sheet = book.add_worksheet('PKAT')
        sheet.write_row(0, 0, HEADERS, head)
        sheet.set_column(0, 0, 8)
        sheet.set_column(1, 2, 16, text)  # kode sebagai teks agar nol di depan tidak hilang
        sheet.set_column(3, N_COLS - 1, 16, money)
        sheet.freeze_panes(1, 3)
        notes = book.add_worksheet('Petunjuk')
        notes.set_column(0, 0, 110)
        for i, line in enumerate([
            "Satu baris per perkiraan. Baris pertama lembar 'PKAT' adalah judul kolom, jangan diubah.",
            "Tahun: tahun anggaran (angka). Kode Stasiun dan No. Perkiraan harus terdaftar dan aktif "
            "pada Unit/PG yang dipilih saat impor.",
            "Barang, Non Barang, Tenaga Kerja, Proyek: komponen anggaran setahun (rupiah, >= 0).",
            "Jan s.d. Des: rencana bulanan. Jumlah 12 bulan harus sama dengan jumlah 4 komponen.",
            "Impor bersifat semua-atau-tidak per stasiun: satu baris gagal membatalkan seluruh "
            "baris stasiun (dan tahun) itu; stasiun lain tetap diimpor.",
            "PKAT stasiun yang masih Draft akan diganti isinya; yang sudah diproses tidak dapat diimpor ulang.",
        ]):
            notes.write(i, 0, line)
        book.close()
        return buf.getvalue()

    def action_download_template(self):
        self.ensure_one()
        self._check_group()
        self.template_file = BinaryBytes(self._build_template(), filename="template_impor_pkat.xlsx")
        return {
            'type': 'ir.actions.act_url',
            'url': '/web/content/%s/%s/template_file/template_impor_pkat.xlsx?download=true' % (
                self._name, self.id),
            'target': 'self',
        }

    # ---------------------------------------------------------------- baca
    def _read_rows(self):
        """Baca lembar pertama menjadi daftar dict baris; galat format sel dicatat per baris."""
        import openpyxl  # pustaka bawaan image Odoo
        if not self.file:
            raise UserError(_("Pilih berkas Excel terlebih dahulu."))
        try:
            book = openpyxl.load_workbook(
                io.BytesIO(self.file.content), read_only=True, data_only=True)  # Odoo 20: BinaryValue, bukan base64
            sheet = book.worksheets[0]
            raw_rows = list(sheet.iter_rows(values_only=True))
        except Exception as exc:  # berkas bukan xlsx / rusak
            raise UserError(_("Berkas tidak dapat dibaca sebagai Excel (.xlsx): %s", exc)) from exc
        if not raw_rows:
            raise UserError(_("Berkas kosong."))
        header = [_cell_text(v).lower() for v in raw_rows[0][:N_COLS]]
        if header != [h.lower() for h in HEADERS]:
            raise UserError(_(
                "Judul kolom tidak sesuai template. Unduh template dan gunakan urutan kolom: %s",
                ', '.join(HEADERS)))
        rows = []
        for number, raw in enumerate(raw_rows[1:], start=2):
            raw = tuple(raw[:N_COLS]) + (None,) * (N_COLS - len(raw[:N_COLS]))
            if all(v is None or _cell_text(v) == '' for v in raw):
                continue
            row = {'number': number, 'raw': raw, 'errors': [],
                   'cost_center_code': _cell_text(raw[1]), 'account_code': _cell_text(raw[2])}
            year = _cell_text(raw[0])
            row['year'] = int(year) if year.isdigit() else None
            if row['year'] is None:
                row['errors'].append(_("Tahun bukan angka: %s", year or '(kosong)'))
            amounts = []
            for label, value in zip(HEADERS[3:], raw[3:]):
                if value is None or value == '':
                    amounts.append(0.0)
                elif isinstance(value, (int, float)) and not isinstance(value, bool):
                    amounts.append(float(value))
                else:
                    amounts.append(0.0)
                    row['errors'].append(_("Kolom %(col)s bukan angka: %(val)s", col=label, val=value))
            row['components'] = amounts[:len(COMPONENTS)]
            row['months'] = amounts[len(COMPONENTS):]
            rows.append(row)
        if not rows:
            raise UserError(_("Tidak ada baris data pada berkas."))
        return rows

    def _resolve_masters(self, rows):
        """FS-PK-02: stasiun dan perkiraan harus terdaftar dan aktif di Unit/PG wizard.
        Isi row['cost_center'] dan row['account']; kode bermasalah -> galat baris."""
        company = self.company_id
        centers = {c.code: c for c in self.env['pkat.cost.center'].with_context(active_test=False).search(
            [('company_id', '=', company.id), ('code', 'in', list({r['cost_center_code'] for r in rows}))])}
        accounts = self.env['account.account']._pkat_find(  # K1: perkiraan = account.account
            company, {r['account_code'] for r in rows}, active_test=False)
        for row in rows:
            for key, found, label in (
                    ('cost_center', centers.get(row['cost_center_code']), _("Stasiun")),
                    ('account', accounts.get(row['account_code']), _("Perkiraan"))):
                code = row[key + '_code'] or _("(kosong)")
                row[key] = found if found and found.active else None
                if not found:
                    row['errors'].append(_(
                        "%(label)s %(code)s tidak terdaftar di %(company)s.",
                        label=label, code=code, company=company.display_name))
                elif not found.active:
                    row['errors'].append(_("%(label)s %(code)s tidak aktif.", label=label, code=code))

    def _validate_rows(self, rows):
        """FS-PK-02: validasi per baris. Galat ditambahkan ke row['errors']."""
        seen = {}
        for row in rows:
            account, center = row['account'], row['cost_center']
            if account and (account.pkat_is_view or account.pkat_needs_completion):
                row['errors'].append(_(
                    "Perkiraan %s adalah perkiraan induk atau belum punya stasiun/bagian di master "
                    "(K8, FS-PK-09).", row['account_code']))
            elif account and center and account.pkat_cost_center_id != center:
                row['errors'].append(_(
                    "Perkiraan %(acc)s bukan milik stasiun %(cc)s (stasiun perkiraan: %(own)s).",
                    acc=row['account_code'], cc=center.code, own=account.pkat_cost_center_id.code))
            key = (row['year'], row['account_code'])
            if key in seen:
                row['errors'].append(_(
                    "Duplikat: perkiraan %(acc)s tahun %(year)s sudah ada di baris %(n)s.",
                    acc=row['account_code'], year=row['year'], n=seen[key]))
            else:
                seen[key] = row['number']
            if any(value < 0 for value in row['components'] + row['months']):
                row['errors'].append(_("Nilai tidak boleh negatif."))
            total_components = sum(row['components'])
            total_months = sum(row['months'])
            if float_compare(total_months, total_components, precision_digits=2) != 0:
                row['errors'].append(_(
                    "Jumlah rencana bulanan (%(months)s) tidak sama dengan jumlah komponen (%(comp)s).",
                    months=formatLang(self.env, total_months, digits=2),
                    comp=formatLang(self.env, total_components, digits=2)))

    def _validate_groups(self, groups):
        """PKAT stasiun yang sudah lewat Draft tidak dapat diimpor ulang (FS-PK-03, FS-PK-04)."""
        states = dict(self.env['pkat.budget']._fields['state'].selection)
        for (year, _code), group in groups.items():
            center = group[0]['cost_center']
            if not center or year is None:
                continue
            budget = self.env['pkat.budget'].search(
                [('cost_center_id', '=', center.id), ('year', '=', year)], limit=1)
            if budget and budget.state != 'draft':
                for row in group:
                    row['errors'].append(_(
                        "PKAT stasiun %(cc)s tahun %(year)s sudah berstatus %(state)s; "
                        "hanya Draft yang dapat diimpor ulang.",
                        cc=center.code, year=year, state=states[budget.state]))

    def _group_rows(self, rows):
        """Kelompok per (tahun, kode stasiun), urut kemunculan."""
        groups = OrderedDict()
        for row in rows:
            groups.setdefault((row['year'], row['cost_center_code']), []).append(row)
        return groups

    # --------------------------------------------------------------- tulis
    def _write_group(self, year, cost_center, rows):
        """Buat (atau ganti isi) pkat.budget draft untuk satu stasiun+tahun."""
        Budget = self.env['pkat.budget']
        budget = Budget.search([('cost_center_id', '=', cost_center.id), ('year', '=', year)], limit=1)
        if budget:
            budget.line_ids.unlink()
        else:
            budget = Budget.create({'cost_center_id': cost_center.id, 'year': year})
        self.env['pkat.budget.line'].create([dict(
            {field: value for (field, _label), value in zip(COMPONENTS, row['components'])},
            budget_id=budget.id,
            account_id=row['account'].id,
            month_ids=[(0, 0, {'month': m, 'amount_plan': plan})
                       for m, plan in enumerate(row['months'], start=1)],
        ) for row in rows])
        return budget

    def action_import(self):
        self.ensure_one()
        self._check_group()
        rows = self._read_rows()
        self._resolve_masters(rows)
        self._validate_rows(rows)
        groups = self._group_rows(rows)
        self._validate_groups(groups)

        # FS-PK-02: semua-atau-tidak per stasiun (dan tahun)
        imported, failed_groups = 0, OrderedDict()
        for key, group in groups.items():
            if not any(row['errors'] for row in group):
                try:
                    with self.env.cr.savepoint():
                        self._write_group(key[0], group[0]['cost_center'], group)
                    imported += len(group)
                    continue
                except (UserError, ValidationError) as exc:
                    group[0]['errors'].append(str(exc))
            failed_groups[key] = group

        failed_rows = [row for group in failed_groups.values() for row in group]
        lines = [_(
            "%(rows)s baris diimpor ke %(n)s PKAT stasiun (status Draft).",
            rows=imported, n=len(groups) - len(failed_groups))]
        vals = {'state': 'done', 'imported_count': imported, 'failed_count': len(failed_rows),
                'error_file': False, 'error_filename': False}
        if failed_rows:
            lines.append(_(
                "%(rows)s baris pada %(n)s stasiun TIDAK diimpor (semua-atau-tidak per stasiun). "
                "Unduh berkas baris gagal, perbaiki, lalu impor ulang berkas itu.",
                rows=len(failed_rows), n=len(failed_groups)))
            shown = [row for row in failed_rows if row['errors']]
            lines += [_("Baris %(n)s: %(err)s", n=row['number'], err='; '.join(row['errors']))
                      for row in shown[:MAX_ERRORS_SHOWN]]
            if len(shown) > MAX_ERRORS_SHOWN:
                lines.append(_("... dan %s baris lain (lihat berkas baris gagal).",
                               len(shown) - MAX_ERRORS_SHOWN))
            vals.update(
                error_file=BinaryBytes(self._build_error_file(failed_rows),
                                       filename='pkat_baris_gagal.xlsx'),
                error_filename='pkat_baris_gagal.xlsx')
        vals['result_message'] = '\n'.join(lines)
        self.write(vals)
        return self._reopen()

    def _build_error_file(self, failed_rows):
        """Berkas baris gagal: kolom sama dengan template + 'Alasan', sehingga setelah
        diperbaiki dapat langsung diimpor ulang (kolom ke-20 diabaikan saat impor)."""
        import xlsxwriter
        buf = io.BytesIO()
        book = xlsxwriter.Workbook(buf, {'in_memory': True})
        head = book.add_format({'bold': True, 'bg_color': '#DDDDDD', 'border': 1})
        sheet = book.add_worksheet('PKAT')
        sheet.write_row(0, 0, HEADERS + ['Alasan'], head)
        sheet.set_column(N_COLS, N_COLS, 90)
        for index, row in enumerate(failed_rows, start=1):
            raw = list(row['raw'])
            raw[1], raw[2] = row['cost_center_code'], row['account_code']  # kode tetap teks
            reason = '; '.join(row['errors']) or _(
                "Tidak diimpor karena baris lain pada stasiun ini gagal.")
            sheet.write_row(index, 0, raw + [reason])
        book.close()
        return buf.getvalue()
