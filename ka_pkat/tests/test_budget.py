"""DM-03/04/05 dan FS-PK-03..09: PKAT stasiun, baris perkiraan, rencana bulanan."""
from odoo.exceptions import ValidationError
from odoo.tests import tagged

from .common import PkatCase


@tagged('post_install', '-at_install')
class TestAccountCompletion(PkatCase):
    """FS-PK-09, K1, K8."""

    def _budget(self):
        return self.env['pkat.budget'].create({'cost_center_id': self.cc_masak.id, 'year': self.year})

    def test_tanda_perlu_dilengkapi(self):
        acc = self._account('5099.240', 'Tanpa stasiun')
        self.assertTrue(acc.pkat_needs_completion)
        self.assertFalse(self.acc_masak_brg.pkat_needs_completion)
        acc.pkat_cost_center_id = self.cc_masak
        self.assertTrue(acc.pkat_needs_completion, "bagian masih kosong")
        acc.pkat_department_id = self.dept_pab
        self.assertFalse(acc.pkat_needs_completion)
        self.assertEqual(
            self.env['account.account'].search_count(
                [('pkat_needs_completion', '=', True), ('pkat_company_id', '=', self.company.id)]), 0)

    def test_perkiraan_belum_lengkap_tidak_bisa_dianggarkan(self):
        acc = self._account('5099.240', 'Tanpa stasiun')
        budget = self._budget()
        with self.assertRaises(ValidationError):
            self.env['pkat.budget.line'].create({'budget_id': budget.id, 'account_id': acc.id})
        line = self.env['pkat.budget.line'].create(
            {'budget_id': budget.id, 'account_id': self.acc_masak_brg.id})
        self.assertEqual(line.wage_type, 'non_upah')

    def test_perkiraan_induk_tidak_bisa_dianggarkan(self):
        """K8/V3."""
        induk = self._account('5025', 'Stasiun Masakan (induk)', pkat_is_view=True)
        with self.assertRaises(ValidationError):
            self.env['pkat.budget.line'].create({'budget_id': self._budget().id, 'account_id': induk.id})

    def test_hanya_perkiraan_pkat_unit_sendiri(self):
        """K1: perkiraan bawaan (bukan pkat_managed) dan perkiraan unit lain ditolak."""
        budget = self._budget()
        biasa = self.env['account.account'].with_company(self.company).create({
            'code': '99990001', 'name': 'Bukan PKAT', 'account_type': 'expense',
            'company_ids': [(6, 0, self.company.ids)]})
        unit_b = self._account('5025.240', 'Milik unit B', company=self.company_b)
        for acc in (biasa, unit_b):
            with self.assertRaises(ValidationError):
                self.env['pkat.budget.line'].create({'budget_id': budget.id, 'account_id': acc.id})
