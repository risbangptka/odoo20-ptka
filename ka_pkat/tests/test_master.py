"""DM-02: validasi master bagian, stasiun, perkiraan."""
from odoo.exceptions import UserError, ValidationError
from odoo.tests import tagged

from .common import PkatCase


@tagged('post_install', '-at_install')
class TestMaster(PkatCase):

    def test_kode_perkiraan_8_digit(self):
        for bad in ('5025004', '502500400', '5025A040', '5025 040'):
            with self.assertRaises(ValidationError, msg=bad):
                self._account(bad, 'salah')

    def test_cost_item_digit_7_8(self):
        self.assertEqual(self.acc_masak_brg.cost_item, '40')
        self.assertEqual(self.acc_masak_upah.cost_item, '01')

    def test_stasiun_dari_digit_3_4(self):
        self.assertEqual(self.acc_masak_brg.cost_center_id, self.cc_masak)
        self.assertEqual(self.acc_masak_brg.department_id, self.dept_pab)
        self.assertEqual(self.acc_ketel_brg.cost_center_id, self.cc_ketel)
        self.assertEqual(self.acc_ketel_brg.department_id, self.dept_ins)

    def test_stasiun_kode_4_digit_didahulukan(self):
        """Kode stasiun gaya Odoo 10 (4 digit pertama perkiraan) menang atas digit 3-4."""
        cc = self.env['pkat.cost.center'].create({
            'code': '5025', 'name': 'St. Masakan (kode 4 digit)',
            'company_id': self.company.id, 'department_id': self.dept_ins.id})
        acc = self._account('50250050', 'Perkiraan lain')
        self.assertEqual(acc.cost_center_id, cc)

    def test_stasiun_tidak_dikenal_dibiarkan_kosong(self):
        acc = self._account('50990040', 'Tanpa stasiun')
        self.assertFalse(acc.cost_center_id)
        self.assertFalse(acc.department_id)

    def test_stasiun_eksplisit_tidak_ditimpa(self):
        acc = self._account('50250060', 'Eksplisit', cost_center_id=self.cc_putar.id)
        self.assertEqual(acc.cost_center_id, self.cc_putar)

    def test_company_harus_sama(self):
        dept_b = self.env['pkat.department'].create(
            {'code': 'PAB', 'name': 'Pabrikasi B', 'company_id': self.company_b.id})
        with self.assertRaises(ValidationError):
            self.env['pkat.cost.center'].create({
                'code': '99', 'name': 'Lintas', 'company_id': self.company.id,
                'department_id': dept_b.id})
        with self.assertRaises(ValidationError):
            self._account('50250070', 'Lintas', department_id=dept_b.id)
        with self.assertRaises(ValidationError):
            self.seksi_masak.parent_id = dept_b
        with self.assertRaises(ValidationError):
            self.acc_masak_brg.company_id = self.company_b

    def test_hierarki_bagian_tanpa_lingkaran(self):
        with self.assertRaises(UserError):  # dijaga core (_parent_store)
            self.dept_pab.parent_id = self.seksi_masak
