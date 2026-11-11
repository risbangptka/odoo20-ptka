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
        return self.env['pkat.budget.import'].with_user(user or self.user_kd).create({
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
            wiz.with_user(self.user_tuk).action_import()

    def test_template_sesuai_kolom(self):
        wiz = self.env['pkat.budget.import'].with_user(self.user_kd).create(
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
        wiz = self.env['pkat.budget.import'].with_user(self.user_kd).create({
            'company_id': self.company.id, 'file': base64.b64encode(b'bukan excel').decode()})
        with self.assertRaises(UserError):
            wiz.action_import()
