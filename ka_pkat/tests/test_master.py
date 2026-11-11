"""DM-02 + PERUBAHAN_DESAIN_01 (K1, K7, K8, V1, V3, V4): master perkiraan, bagian, stasiun."""
from psycopg2 import IntegrityError

from odoo.exceptions import ValidationError
from odoo.tests import tagged
from odoo.tools import mute_logger

from .common import PkatCase


@tagged('post_install', '-at_install')
class TestMaster(PkatCase):

    # ------------------------------------------------- K1/V1: account.account
    def test_perkiraan_adalah_account_account(self):
        acc = self.acc_masak_brg
        self.assertEqual(acc._name, 'account.account')
        self.assertTrue(acc.pkat_managed)
        self.assertEqual(acc.pkat_company_id, self.company)
        self.assertEqual(acc.company_ids, self.company)
        self.assertNotIn('pkat.account', self.env.registry)
        self.assertNotIn('pkat.department', self.env.registry)

    def test_v1_kode_sama_pada_dua_unit_bersaudara(self):
        """V1: dua unit di bawah induk yang sama boleh punya perkiraan berkode sama."""
        acc_b = self._account('5025.240', 'Bahan Pembantu Masakan (unit B)', company=self.company_b)
        self.assertNotEqual(acc_b, self.acc_masak_brg)
        self.assertEqual(acc_b.pkat_company_id, self.company_b)
        self.assertEqual(acc_b._pkat_code(), self.acc_masak_brg._pkat_code())
        found = self.env['account.account']._pkat_find(self.company_b, ['5025.240'])
        self.assertEqual(found['5025.240'], acc_b)

    def test_v1_kode_unik_dalam_satu_unit(self):
        with self.assertRaises(ValidationError):  # dijaga core (_ensure_code_is_unique)
            self._account('5025.240', 'Duplikat')

    def test_v1_tepat_satu_company(self):
        with self.assertRaises(ValidationError):
            self.acc_masak_brg.company_ids = self.company | self.company_b

    def test_v1_ka10_id_unik_per_unit(self):
        self.acc_masak_brg.ka10_id = 4711
        self._account('5025.241', 'Unit lain boleh', company=self.company_b, ka10_id=4711)
        with self.assertRaises(IntegrityError), mute_logger('odoo.sql_db'):
            self.acc_putar_brg.ka10_id = 4711
            self.env.flush_all()

    def test_kode_tidak_bergantung_company_aktif(self):
        """Kode account.account disimpan per company root; _pkat_code/_pkat_find tetap benar
        walaupun company aktif berasal dari root lain."""
        lain = self.env['res.company'].create({'name': 'Root Lain', 'code': 'UJ9'})
        acc = self.acc_masak_brg.with_company(lain)
        self.assertFalse(acc.code)
        self.assertEqual(acc._pkat_code(), '5025.240')
        found = self.env['account.account'].with_company(lain)._pkat_find(self.company, ['5025.240'])
        self.assertEqual(found.get('5025.240'), self.acc_masak_brg)

    def test_v4_tidak_membuat_jurnal_otomatis(self):
        Journal = self.env['account.journal'].with_context(active_test=False)
        before = Journal.search_count([])
        self._account('11100001', 'Kas Unit', account_type='asset_cash')
        self._account('21900001', 'Kartu Kredit', account_type='liability_credit_card')
        self.assertEqual(Journal.search_count([]), before)
        # pembanding: tanpa _pkat_create, core membuat jurnal untuk perkiraan kas
        self.env['account.account'].with_company(self.company).create({
            'code': '11100002', 'name': 'Kas biasa', 'account_type': 'asset_cash',
            'company_ids': [(6, 0, self.company.ids)]})
        self.assertEqual(Journal.search_count([]), before + 1)

    def test_perkiraan_bawaan_bukan_pkat(self):
        acc = self.env['account.account'].with_company(self.company).with_context(
            skip_auto_account_journal_creation=True).create({
                'code': '99990001', 'name': 'Bukan PKAT', 'account_type': 'expense',
                'company_ids': [(6, 0, self.company.ids)]})
        self.assertFalse(acc.pkat_managed)
        self.assertFalse(acc.pkat_needs_completion)
        self.assertFalse(acc.pkat_cost_center_id)
        self.assertNotIn('99990001', self.env['account.account']._pkat_find(self.company, ['99990001']))

    # ------------------------------------------------------ K8/V3: induk
    def test_v3_perkiraan_induk(self):
        induk = self._account('5025', 'Stasiun Masakan (induk)', pkat_is_view=True)
        self.assertFalse(induk.pkat_needs_completion)
        self.assertFalse(induk.pkat_cost_center_id)
        self.acc_masak_brg.parent_id = induk
        self.assertEqual(self.acc_masak_brg.parent_id, induk)
        self.assertIn(self.acc_masak_brg, self.env['account.account'].search(
            [('id', 'child_of', induk.id), ('pkat_is_view', '=', False)]))

    # --------------------------------------------- DM-02: stasiun dan bagian
    def test_k5_jenis_biaya_karakter_7_8(self):
        self.assertEqual(self.acc_masak_brg.pkat_cost_item, '40')
        self.assertEqual(self.acc_masak_upah.pkat_cost_item, '01')
        # kode 9 karakter (NNNN.NNNN): tetap karakter 7-8, bukan 2 karakter terakhir
        self.assertEqual(self._account('5025.2441', 'Kode 9 karakter').pkat_cost_item, '44')
        # perkiraan induk / kode di luar pola: tanpa jenis biaya
        self.assertFalse(self._account('5025', 'Induk', pkat_is_view=True).pkat_cost_item)
        self.assertFalse(self._account('50250040', 'Tanpa titik').pkat_cost_item)

    def test_k5_tidak_ada_validasi_8_digit(self):
        for code in ('5010.444', '5010.4441', '5025', '1'):
            self._account(code, 'Kode %s' % code, pkat_is_view=len(code) < 8)

    def test_v10_upah_dari_jenis_biaya(self):
        """V10: jenis biaya 00-07 = upah, juga untuk kode 9 karakter; awalan 4001 = upah."""
        kasus = {
            '5025.200': 'upah', '5025.207': 'upah', '5025.208': 'non_upah', '5025.240': 'non_upah',
            '5022.4031': 'upah',       # Odoo 10 keliru menganggapnya non_upah (kode dipotong)
            '5022.4081': 'non_upah',
            '4001.250': 'upah',        # 4 karakter pertama 4001
            '4002.250': 'non_upah',
        }
        for code, expected in kasus.items():
            acc = self.env['account.account']._pkat_find(self.company, [code]).get(code) \
                or self._account(code, 'Uji %s' % code)
            self.assertEqual(acc.pkat_wage_type, expected, code)
        self.assertEqual(self.acc_masak_upah.pkat_wage_type, 'upah')

    def test_v10_upah_ikut_berubah_bila_kode_berubah(self):
        acc = self._account('5025.250', 'Berubah kode')
        self.assertEqual(acc.pkat_wage_type, 'non_upah')
        acc.with_company(self.company).code = '5025.205'
        self.assertEqual((acc.pkat_cost_item, acc.pkat_wage_type), ('05', 'upah'))

    def test_v2_stasiun_4_karakter_pertama(self):
        """V2: bukan digit 3-4. Stasiun berkode '25' tidak boleh terpilih untuk 5025.xxx."""
        self.env['pkat.cost.center'].create({
            'code': '25', 'name': 'Kode 2 digit (keliru)', 'company_id': self.company.id,
            'department_id': self.dept_ins.id})
        acc = self._account('5025.261', 'Perkiraan lain')
        self.assertEqual(acc.pkat_cost_center_id, self.cc_masak)
        self.assertEqual(self._account('5025.2611', 'Kode 9 karakter').pkat_cost_center_id, self.cc_masak)

    def test_stasiun_dan_bagian_diturunkan(self):
        self.assertEqual(self.acc_masak_brg.pkat_cost_center_id, self.cc_masak)
        self.assertEqual(self.acc_masak_brg.pkat_department_id, self.dept_pab)
        self.assertEqual(self.acc_ketel_brg.pkat_cost_center_id, self.cc_ketel)
        self.assertEqual(self.acc_ketel_brg.pkat_department_id, self.dept_ins)

    def test_stasiun_tidak_dikenal_dibiarkan_kosong(self):
        acc = self._account('5099.240', 'Tanpa stasiun')
        self.assertFalse(acc.pkat_cost_center_id)
        self.assertFalse(acc.pkat_department_id)

    def test_stasiun_eksplisit_tidak_ditimpa(self):
        acc = self._account('5025.260', 'Eksplisit', pkat_cost_center_id=self.cc_putar.id)
        self.assertEqual(acc.pkat_cost_center_id, self.cc_putar)

    def test_company_harus_sama(self):
        dept_b = self._department('PAB', 'Pabrikasi B', company=self.company_b)
        with self.assertRaises(ValidationError):
            self.env['pkat.cost.center'].create({
                'code': '99', 'name': 'Lintas', 'company_id': self.company.id,
                'department_id': dept_b.id})
        with self.assertRaises(ValidationError):
            self._account('5025.270', 'Lintas', pkat_department_id=dept_b.id)
        with self.assertRaises(ValidationError):
            self.acc_masak_brg.pkat_department_id = dept_b

    # ------------------------------------------------- K7/V9: hr.department
    def test_bagian_adalah_hr_department(self):
        self.assertEqual(self.dept_pab._name, 'hr.department')
        self.assertEqual(self.dept_pab.pkat_code, 'PAB')
        self.assertEqual(self.seksi_masak.parent_id, self.dept_pab)
        self.assertIn(self.seksi_masak, self.env['hr.department'].search(
            [('id', 'child_of', self.dept_pab.id)]))
        user = self._user('uji_kabag', 'group_pkat_pengguna')
        self.dept_pab.pkat_manager_user_id = user
        self.assertEqual(self.dept_pab.pkat_manager_user_id, user)

    def test_ka10_id_bagian_dan_stasiun_unik(self):
        self.dept_pab.ka10_id = 12
        self.cc_masak.ka10_id = 7
        with self.assertRaises(IntegrityError), mute_logger('odoo.sql_db'):
            self.dept_ins.ka10_id = 12
            self.env.flush_all()
