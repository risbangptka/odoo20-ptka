"""FS-PK-01, FS-PK-02: impor PKAT dari Excel."""
import base64
import io

import openpyxl

from odoo.exceptions import AccessError, UserError
from odoo.tests import tagged

from ..wizard.pkat_budget_import import HEADERS
from .common import PkatCase

JT = 1000000.0


def rata(total):
    """12 rencana bulanan sama rata."""
    return [total / 12.0] * 12


@tagged('post_install', '-at_install')
class TestImport(PkatCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user_kd = cls._user('uji_kd', 'group_pkat_anggaran_kd')
        cls.user_tuk = cls._user('uji_tuk', 'group_pkat_tuk_unit')

    # ------------------------------------------------------------- helper
    def _xlsx(self, rows, headers=HEADERS):
        book = openpyxl.Workbook()
        sheet = book.active
        sheet.append(list(headers))
        for row in rows:
            sheet.append(list(row))
        buf = io.BytesIO()
        book.save(buf)
        return base64.b64encode(buf.getvalue()).decode()  # str base64 = cara klien web mengirim

    def _row(self, cc, account, goods=0.0, nongoods=0.0, wage=0.0, project=0.0, months=None, year=None):
        total = goods + nongoods + wage + project
        return [year or self.year, cc, account, goods, nongoods, wage, project] + (
            months if months is not None else rata(total))

    def _wizard(self, rows, user=None, **kw):
        return self.env['pkat.budget.import'].with_user(user or self.user_kd).with_context(allowed_company_ids=self.company.ids).create({
            'company_id': self.company.id, 'file': self._xlsx(rows, **kw), 'filename': 'pkat.xlsx'})

    def _budget(self, cc, year=None):
        return self.env['pkat.budget'].search(
            [('cost_center_id', '=', cc.id), ('year', '=', year or self.year)])

    # ------------------------------------------------------------ FS-PK-01
    def test_impor_berhasil(self):
        wiz = self._wizard([
            self._row('25', '50250040', goods=60 * JT, nongoods=40 * JT),
            self._row('25', '50250001', wage=24 * JT),
            self._row('31', 50310040, goods=12 * JT),  # kode perkiraan sebagai angka Excel
        ])
        wiz.action_import()
        self.assertEqual(wiz.state, 'done')
        self.assertEqual(wiz.imported_count, 3)
        masak = self._budget(self.cc_masak)
        self.assertEqual(masak.state, 'draft')
        self.assertEqual(len(masak.line_ids), 2)
        line = masak.line_ids.filtered(lambda l: l.account_id == self.acc_masak_brg)
        self.assertEqual((line.amount_goods, line.amount_nongoods), (60 * JT, 40 * JT))
        self.assertEqual(line.amount_initial, 100 * JT)
        self.assertEqual(line.amount_current, 100 * JT)
        self.assertEqual(line.month_ids.mapped('month'), list(range(1, 13)))
        self.assertAlmostEqual(sum(line.month_ids.mapped('amount_plan')), 100 * JT, places=2)
        self.assertEqual(masak.amount_current, 124 * JT)
        self.assertEqual(self._budget(self.cc_ketel).amount_current, 12 * JT)

    def test_impor_ulang_mengganti_draft(self):
        self._wizard([self._row('25', '50250040', goods=60 * JT)]).action_import()
        self._wizard([self._row('25', '50250001', wage=10 * JT)]).action_import()
        masak = self._budget(self.cc_masak)
        self.assertEqual(len(masak), 1)
        self.assertEqual(masak.line_ids.account_id, self.acc_masak_upah)

    def test_hanya_anggaran_kd(self):
        with self.assertRaises(AccessError):
            self._wizard([self._row('25', '50250040', goods=JT)], user=self.user_tuk)
        wiz = self._wizard([self._row('25', '50250040', goods=JT)])
        with self.assertRaises(AccessError):
            wiz.with_user(self.user_tuk).with_context(allowed_company_ids=self.company.ids).action_import()

    def test_template_sesuai_kolom(self):
        wiz = self.env['pkat.budget.import'].with_user(self.user_kd).with_context(allowed_company_ids=self.company.ids).create(
            {'company_id': self.company.id})
        action = wiz.action_download_template()
        self.assertIn('/web/content/pkat.budget.import/%s/template_file/' % wiz.id, action['url'])
        book = openpyxl.load_workbook(io.BytesIO(wiz.template_file.content))
        self.assertEqual([c.value for c in book.worksheets[0][1]], HEADERS)
        # template kosong yang diunggah kembali ditolak dengan pesan jelas
        wiz.file = wiz.template_file
        with self.assertRaises(UserError):
            wiz.action_import()

    def test_judul_kolom_salah(self):
        wiz = self._wizard([self._row('25', '50250040', goods=JT)], headers=HEADERS[1:] + HEADERS[:1])
        with self.assertRaises(UserError):
            wiz.action_import()

    def test_bukan_excel(self):
        wiz = self.env['pkat.budget.import'].with_user(self.user_kd).with_context(allowed_company_ids=self.company.ids).create({
            'company_id': self.company.id, 'file': base64.b64encode(b'bukan excel').decode()})
        with self.assertRaises(UserError):
            wiz.action_import()

    # ------------------------------------------------------------ FS-PK-02
    def _gagal(self, rows):
        """Impor yang seluruhnya gagal; kembalikan (wizard, alasan per nomor baris Excel)."""
        wiz = self._wizard(rows)
        wiz.action_import()
        self.assertEqual(wiz.state, 'done')
        return wiz, self._alasan(wiz)

    def _alasan(self, wiz):
        book = openpyxl.load_workbook(io.BytesIO(wiz.error_file.content))
        rows = list(book.worksheets[0].iter_rows(values_only=True))
        self.assertEqual(list(rows[0]), HEADERS + ['Alasan'])
        return [row[-1] for row in rows[1:]]

    def test_stasiun_dan_perkiraan_harus_terdaftar_dan_aktif(self):
        self.acc_putar_brg.active = False
        wiz, alasan = self._gagal([
            self._row('77', '50250040', goods=JT),
            self._row('25', '50259999', goods=JT),
            self._row('26', '50260040', goods=JT),
        ])
        self.assertEqual((wiz.imported_count, wiz.failed_count), (0, 3))
        self.assertIn('Stasiun 77 tidak terdaftar', alasan[0])
        self.assertIn('Perkiraan 50259999 tidak terdaftar', alasan[1])
        self.assertIn('Perkiraan 50260040 tidak aktif', alasan[2])
        self.assertFalse(self.env['pkat.budget'].search([('company_id', '=', self.company.id)]))

    def test_perkiraan_harus_milik_stasiun(self):
        _wiz, alasan = self._gagal([self._row('26', '50250040', goods=JT)])
        self.assertIn('bukan milik stasiun 26', alasan[0])

    def test_perkiraan_unit_lain_ditolak(self):
        cc_b = self.env['pkat.cost.center'].create({
            'code': '25', 'name': 'St. Masakan B', 'company_id': self.company_b.id,
            'department_id': self._department('PAB', 'Pabrikasi B', company=self.company_b).id})
        self._account('50250099', 'Milik unit B', company=self.company_b)
        _wiz, alasan = self._gagal([self._row('25', '50250099', goods=JT)])
        self.assertIn('Perkiraan 50250099 tidak terdaftar', alasan[0])
        self.assertFalse(self._budget(cc_b))

    def test_duplikat(self):
        _wiz, alasan = self._gagal([
            self._row('25', '50250040', goods=JT),
            self._row('25', '50250040', goods=2 * JT),
        ])
        self.assertIn('Tidak diimpor karena baris lain', alasan[0])
        self.assertIn('Duplikat', alasan[1])
        self.assertIn('baris 2', alasan[1])

    def test_nilai_negatif_dan_bukan_angka(self):
        _wiz, alasan = self._gagal([
            self._row('25', '50250040', goods=-12 * JT),
            [self.year, '25', '50250001', 0.0, 0.0, 'dua belas juta', 0.0] + [0.0] * 12,
        ])
        self.assertIn('negatif', alasan[0])
        self.assertIn('Kolom Tenaga Kerja bukan angka', alasan[1])

    def test_total_bulanan_harus_sama_dengan_komponen(self):
        """FS-PK-02: impor MENOLAK baris bila total bulanan != total komponen."""
        _wiz, alasan = self._gagal([
            self._row('25', '50250040', goods=120 * JT, months=[10 * JT] * 11 + [9 * JT]),
        ])
        self.assertIn('Jumlah rencana bulanan', alasan[0])
        self.assertFalse(self._budget(self.cc_masak))
        # selisih pembulatan di bawah 1 sen diterima
        wiz = self._wizard([self._row('25', '50250040', goods=100 * JT, months=rata(100 * JT))])
        wiz.action_import()
        self.assertEqual((wiz.imported_count, wiz.failed_count), (1, 0))
        self.assertFalse(wiz.error_file)

    def test_semua_atau_tidak_per_stasiun(self):
        wiz = self._wizard([
            self._row('25', '50250040', goods=60 * JT),
            self._row('25', '50250001', wage=-JT),            # gagal -> seluruh St. Masakan batal
            self._row('31', '50310040', goods=12 * JT),       # St. Ketel tetap masuk
            self._row('26', '50260040', goods=6 * JT),        # St. Putaran tetap masuk
        ])
        wiz.action_import()
        self.assertEqual((wiz.imported_count, wiz.failed_count), (2, 2))
        self.assertFalse(self._budget(self.cc_masak))
        self.assertEqual(self._budget(self.cc_ketel).amount_current, 12 * JT)
        self.assertEqual(self._budget(self.cc_putar).amount_current, 6 * JT)
        alasan = self._alasan(wiz)
        self.assertEqual(len(alasan), 2)
        self.assertIn('Baris 3', wiz.result_message)
        # berkas baris gagal dapat langsung diimpor ulang setelah diperbaiki
        book = openpyxl.load_workbook(io.BytesIO(wiz.error_file.content))
        sheet = book.worksheets[0]
        sheet.cell(row=3, column=6).value = JT          # Tenaga Kerja
        for col in range(8, 20):
            sheet.cell(row=3, column=col).value = JT / 12.0
        buf = io.BytesIO()
        book.save(buf)
        ulang = self.env['pkat.budget.import'].with_user(self.user_kd).with_context(allowed_company_ids=self.company.ids).create({
            'company_id': self.company.id, 'file': base64.b64encode(buf.getvalue()).decode()})
        ulang.action_import()
        self.assertEqual((ulang.imported_count, ulang.failed_count), (2, 0))
        self.assertEqual(self._budget(self.cc_masak).amount_current, 61 * JT)

    def test_pkat_yang_sudah_diproses_tidak_dapat_diimpor_ulang(self):
        self._wizard([self._row('25', '50250040', goods=60 * JT)]).action_import()
        masak = self._budget(self.cc_masak)
        masak.action_proses()
        _wiz, alasan = self._gagal([self._row('25', '50250040', goods=70 * JT)])
        self.assertIn('sudah berstatus Proses', alasan[0])
        self.assertEqual(masak.amount_current, 60 * JT)

    def test_tahun_berbeda_dikelompokkan_terpisah(self):
        wiz = self._wizard([
            self._row('25', '50250040', goods=60 * JT),
            self._row('25', '50250040', goods=-JT, year=self.year + 1),
        ])
        wiz.action_import()
        self.assertEqual((wiz.imported_count, wiz.failed_count), (1, 1))
        self.assertTrue(self._budget(self.cc_masak))
        self.assertFalse(self._budget(self.cc_masak, self.year + 1))
