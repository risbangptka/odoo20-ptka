"""Uji aturan keputusan (SRS TS-01 s.d. TS-05, TS-16). Python murni:
    python -m unittest ka_pkat/tests/test_engine.py      (dari akar addons20)
Odoo juga akan menjalankannya lewat --test-enable.
"""
import os
import sys
import unittest

try:
    from ..services import engine
except (ImportError, ValueError):  # dijalankan langsung tanpa Odoo
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'services'))
    import engine

JT = 1000000.0


def line(amount, pocket, account=None, month=3, **kw):
    vals = {'ref': 'x', 'amount': amount, 'month': month, 'pocket': pocket,
            'account': account if account is not None else pocket}
    vals.update(kw)
    return vals


class TestKasusBRD(unittest.TestCase):
    """BRD 2.6: Kantung St. Masakan Rp100 juta, dasar tahunan."""

    def setUp(self):
        self.serapan = engine.Position('masakan', 100 * JT, used=[0.0] * 12)
        self.realisasi = engine.Position('masakan', 100 * JT, used=[0.0] * 12)

    def _po(self, amount):
        res = engine.check_document(engine.KIND_PO, [line(amount, self.serapan)])
        if res['status'] != 'reject':
            self.serapan.used[2] += amount
        return res

    def _bon(self, amount):
        res = engine.check_document(engine.KIND_REAL, [line(amount, self.realisasi)])
        if res['status'] != 'reject':
            self.realisasi.used[2] += amount
        return res

    def _spm(self, amount):
        return engine.check_document(engine.KIND_SPM, [line(amount, self.serapan)])

    def test_kasus_4_tahap(self):
        # tahap 1
        self.assertEqual(self._spm(30 * JT)['code'], engine.OK)
        self.assertEqual(self._po(30 * JT)['code'], engine.OK)
        self.assertEqual(self._bon(30 * JT)['code'], engine.OK)
        # tahap 2: SPM 80 -> potensi 110% -> peringatan, tidak dikunci
        self.assertEqual(self._spm(80 * JT)['code'], engine.WARN_POCKET_OVER)
        self.assertEqual(self._po(50 * JT)['code'], engine.OK)
        self.assertEqual(self._bon(30 * JT)['code'], engine.OK)
        # tahap 3: serapan tepat 100% diperbolehkan
        self.assertEqual(self._spm(50 * JT)['code'], engine.WARN_POCKET_OVER)
        self.assertEqual(self._po(20 * JT)['code'], engine.OK)
        self.assertEqual(self._bon(20 * JT)['code'], engine.OK)
        self.assertEqual(sum(self.serapan.used), 100 * JT)
        self.assertEqual(sum(self.realisasi.used), 80 * JT)
        # tahap 4: PO dan bon ditolak
        self.assertEqual(self._po(20 * JT)['code'], engine.REJECT_POCKET_OVER)
        self.assertEqual(self._bon(30 * JT)['code'], engine.REJECT_POCKET_OVER)
        self.assertEqual(sum(self.serapan.used), 100 * JT)


class TestAturan(unittest.TestCase):

    def test_tanpa_anggaran(self):
        for kind in (engine.KIND_SPM, engine.KIND_PO, engine.KIND_REAL):
            res = engine.check_document(kind, [{'ref': 1, 'amount': 1, 'month': 1,
                                                'account': None, 'pocket': None}])
            self.assertEqual(res['code'], engine.REJECT_NO_BUDGET)

    def test_perkiraan_lebih_kantung_cukup(self):
        pocket = engine.Position('bagian', 100 * JT)
        account = engine.Position('akun', 10 * JT, used=[9 * JT] + [0.0] * 11)
        res = engine.check_document(engine.KIND_PO, [line(5 * JT, pocket, account)])
        self.assertEqual(res['code'], engine.WARN_ACCOUNT_OVER)
        self.assertEqual(res['status'], 'warn')

    def test_tidak_dikendalikan(self):
        res = engine.check_document(engine.KIND_PO, [{'ref': 1, 'amount': 999 * JT, 'controlled': False}])
        self.assertEqual(res['code'], engine.PASS_UNCONTROLLED)

    def test_dasar_ytd_mtd(self):
        plan = [10 * JT] * 12
        pocket = engine.Position('p', 120 * JT, plan=plan, used=[10 * JT, 5 * JT] + [0.0] * 10)
        # Maret: ytd batas 30, terpakai 15 -> 15 lolos, 16 ditolak
        ok = engine.check_document(engine.KIND_PO, [line(15 * JT, pocket, month=3)], basis='ytd')
        no = engine.check_document(engine.KIND_PO, [line(16 * JT, pocket, month=3)], basis='ytd')
        self.assertEqual((ok['code'], no['code']), (engine.OK, engine.REJECT_POCKET_OVER))
        # Februari: mtd batas 10, terpakai 5
        ok = engine.check_document(engine.KIND_PO, [line(5 * JT, pocket, month=2)], basis='mtd')
        no = engine.check_document(engine.KIND_PO, [line(6 * JT, pocket, month=2)], basis='mtd')
        self.assertEqual((ok['code'], no['code']), (engine.OK, engine.REJECT_POCKET_OVER))
        # tahunan: masih jauh
        res = engine.check_document(engine.KIND_PO, [line(100 * JT, pocket, month=2)], basis='yearly')
        self.assertEqual(res['code'], engine.OK)

    def test_kumulatif_antar_baris(self):
        pocket = engine.Position('p', 100 * JT, used=[50 * JT] + [0.0] * 11)
        res = engine.check_document(engine.KIND_PO, [line(30 * JT, pocket), line(30 * JT, pocket)])
        self.assertEqual([l['code'] for l in res['lines']], [engine.OK, engine.REJECT_POCKET_OVER])
        self.assertEqual(res['status'], 'reject')

    def test_kunci_manual(self):
        pocket = engine.Position('p', 100 * JT)
        res = engine.check_document(engine.KIND_PO, [line(1 * JT, pocket, manual_lock=True)])
        self.assertEqual(res['code'], engine.REJECT_MANUAL_LOCK)
        res = engine.check_document(engine.KIND_SPM, [line(1 * JT, pocket, manual_lock=True)])
        self.assertEqual(res['code'], engine.OK)

    def test_proyek(self):
        proyek = engine.Position('INV-1', 100 * JT, used=[90 * JT] + [0.0] * 11)
        base = {'ref': 1, 'month': 1, 'account': None, 'pocket': None, 'project': proyek}
        res = engine.check_document(engine.KIND_PO, [dict(base, amount=10 * JT)])
        self.assertEqual(res['code'], engine.OK)
        res = engine.check_document(engine.KIND_PO, [dict(base, amount=11 * JT)])
        self.assertEqual(res['code'], engine.REJECT_PROJECT_OVER)
        res = engine.check_document(engine.KIND_SPM, [dict(base, amount=11 * JT)])
        self.assertEqual(res['code'], engine.WARN_POCKET_OVER)
        res = engine.check_document(engine.KIND_REAL, [dict(base, amount=1, project_closed=True)])
        self.assertEqual(res['code'], engine.REJECT_PROJECT_CLOSED)

    def test_po_plb_cek_proyek_dan_kantung(self):
        proyek = engine.Position('PLB-1', 100 * JT)
        pocket = engine.Position('p', 10 * JT)
        res = engine.check_document(engine.KIND_PO, [
            {'ref': 1, 'amount': 20 * JT, 'month': 1, 'project': proyek, 'account': pocket, 'pocket': pocket}])
        self.assertEqual(res['code'], engine.REJECT_POCKET_OVER)

    def test_ews(self):
        self.assertEqual([engine.ews_color(p) for p in (75, 75.1, 100, 100.1)],
                         ['green', 'yellow', 'yellow', 'red'])


if __name__ == '__main__':
    unittest.main()
