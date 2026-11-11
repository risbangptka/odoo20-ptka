"""DM-03/04/05 dan FS-PK-03..09: PKAT stasiun, baris perkiraan, rencana bulanan."""
from odoo.exceptions import ValidationError
from odoo.tests import tagged

from .common import PkatCase


@tagged('post_install', '-at_install')
class TestAccountCompletion(PkatCase):
    """FS-PK-09."""

    def test_tanda_perlu_dilengkapi(self):
        acc = self._account('50990040', 'Tanpa stasiun')
        self.assertTrue(acc.needs_completion)
        self.assertFalse(self.acc_masak_brg.needs_completion)
        acc.cost_center_id = self.cc_masak
        self.assertTrue(acc.needs_completion, "bagian masih kosong")
        acc.department_id = self.dept_pab
        self.assertFalse(acc.needs_completion)
        self.assertEqual(
            self.env['pkat.account'].search_count(
                [('needs_completion', '=', True), ('company_id', '=', self.company.id)]), 0)

    def test_perkiraan_belum_lengkap_tidak_bisa_dianggarkan(self):
        acc = self._account('50990040', 'Tanpa stasiun')
        budget = self.env['pkat.budget'].create({'cost_center_id': self.cc_masak.id, 'year': self.year})
        with self.assertRaises(ValidationError):
            self.env['pkat.budget.line'].create({'budget_id': budget.id, 'account_id': acc.id})
        self.env['pkat.budget.line'].create(
            {'budget_id': budget.id, 'account_id': self.acc_masak_brg.id})
