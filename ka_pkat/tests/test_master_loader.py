"""Pemuatan master dari ekspor Odoo 10 (K3, V1, V3, V4, V5, V6, V10)."""
from odoo.tests import tagged

from .common import PkatCase

T = 'account.data_account_type_'
VIEW = 'ka_account.data_account_type_view'
UNPOSTABLE = 'ka_account.data_account_type_unpostable'


@tagged('post_install', '-at_install')
class TestMasterLoader(PkatCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Loader = cls.env['pkat.master.loader']
        cls.code_a, cls.code_b = cls.company.code, cls.company_b.code

    # ------------------------------------------------------------ helper
    def _dept(self, id_, name, parent=None, company=None, bagian=None, active='t'):
        return {'id': str(id_), 'name': name, 'code': '', 'parent_id': parent and str(parent) or '',
                'company_code': company or self.code_a, 'active': active, 'bagian_kode': bagian or ''}

    def _cc(self, id_, kode, name, dept, company=None, seksi=None, sub=None, active='t'):
        return {'id': str(id_), 'kode': kode, 'name': name, 'company_code': company or self.code_a,
                'bagian_kode': '', 'department_id': str(dept or ''), 'seksi_id': str(seksi or ''),
                'sub_seksi_id': str(sub or ''), 'active': active}

    def _acc(self, id_, code, name, type_='expenses', parent=None, company=None, stasiun=None,
             bagian=None, upah='non_upah', deprecated='f'):
        xmlid = type_ if '.' in type_ else T + type_
        return {'id': str(id_), 'code': code, 'name': name, 'company_code': company or self.code_a,
                'parent_id': parent and str(parent) or '', 'type_xmlid': xmlid, 'type_name': type_,
                'type_internal': 'other', 'stasiun_id': str(stasiun or ''), 'bagian_id': str(bagian or ''),
                'upah': upah, 'is_detail': 't', 'deprecated': deprecated}

    def _muat_dasar(self):
        self.Loader.load_departments([
            self._dept(901, 'Bagian Teknik', bagian='203'),
            self._dept(902, 'Seksi Listrik', parent=901),
            self._dept(903, 'Sub Seksi Gardu', parent=902),
        ])
        self.Loader.load_cost_centers([
            self._cc(801, '6010', 'St. Listrik', dept=901, seksi=902, sub=903),
        ])

    def _akun(self, ka10_id, company=None):
        return self.env['account.account'].with_context(active_test=False).search([
            ('ka10_id', '=', ka10_id), ('pkat_company_id', '=', (company or self.company).id)])

    # --------------------------------------------------------- departemen
    def test_departemen_dan_stasiun(self):
        self._muat_dasar()
        Dept = self.env['hr.department']
        bagian = Dept.search([('ka10_id', '=', 901)])
        sub = Dept.search([('ka10_id', '=', 903)])
        self.assertEqual(bagian.pkat_code, '203')
        self.assertEqual(bagian.company_id, self.company)
        self.assertEqual(sub.parent_id.parent_id, bagian)
        cc = self.env['pkat.cost.center'].search([('ka10_id', '=', 801)])
        self.assertEqual((cc.code, cc.department_id, cc.subsection_id), ('6010', bagian, sub))

    def test_stasiun_ditolak_dengan_alasan(self):
        self._muat_dasar()
        report = self.Loader.load_cost_centers([
            self._cc(801, '6010', 'St. Listrik', dept=901),
            self._cc(802, '6010', 'Kode dobel', dept=901),
            self._cc(803, '6011', 'Tanpa bagian', dept=None),
            self._cc(804, '6012', 'Unit tidak ada', dept=901, company='ZZ'),
        ])
        self.assertEqual(report['updated'], 1)
        alasan = [reason for _row, reason in report['rejected']]
        self.assertEqual(len(alasan), 3)
        self.assertIn('dobel', alasan[0])
        self.assertIn('tidak dimuat', alasan[1])
        self.assertIn('ZZ', alasan[2])

    # ---------------------------------------------------------- perkiraan
    def test_perkiraan_dimuat_dan_idempoten(self):
        self._muat_dasar()
        rows = [
            self._acc(701, '6010', 'STASIUN LISTRIK', VIEW),
            self._acc(702, '6010.240', 'Bahan Listrik', 'direct_costs', parent=701, stasiun=801, bagian=901),
            self._acc(703, '6010.201', 'Upah Listrik', 'direct_costs', parent=701, upah='upah'),
            self._acc(704, '4500.200', 'Pendapatan Lain', 'other_income'),
            self._acc(705, '1100.200', 'Bank', 'liquidity', deprecated='t'),
        ]
        journals = self.env['account.journal'].with_context(active_test=False).search_count([])
        report = self.Loader.load_accounts(rows)
        self.assertEqual((report['created'], report['updated'], report['rejected']), (5, 0, []))
        # V4: tidak ada jurnal otomatis walau ada perkiraan kas/bank
        self.assertEqual(
            self.env['account.journal'].with_context(active_test=False).search_count([]), journals)
        induk, bahan, upah = self._akun(701), self._akun(702), self._akun(703)
        self.assertTrue(induk.pkat_is_view)
        self.assertEqual(induk.account_type, 'expense_direct_cost', "V3: tipe anak terbanyak")
        self.assertFalse(induk.pkat_kind)
        self.assertEqual(bahan.parent_id, induk)
        self.assertEqual(bahan.pkat_cost_center_id.ka10_id, 801)
        self.assertEqual(bahan.pkat_department_id.ka10_id, 901)
        self.assertEqual((bahan.pkat_kind, bahan.pkat_wage_type, bahan.pkat_cost_item),
                         ('expense', 'non_upah', '40'))
        # stasiun/bagian kosong di Odoo 10 -> diturunkan dari 4 karakter pertama kode (V2)
        self.assertEqual(upah.pkat_cost_center_id.ka10_id, 801)
        self.assertEqual(upah.pkat_wage_type, 'upah')
        self.assertEqual(self._akun(704).pkat_kind, 'income')
        bank = self._akun(705)
        self.assertEqual((bank.account_type, bank.active, bank.pkat_kind), ('asset_cash', False, False))
        self.assertTrue(all(a.company_ids == self.company for a in induk | bahan | upah | bank))
        # muat ulang: tidak ada duplikat, nama ikut diperbarui
        rows[1]['name'] = 'Bahan Listrik (revisi)'
        again = self.Loader.load_accounts(rows)
        self.assertEqual((again['created'], again['updated'], again['rejected']), (0, 5, []))
        self.assertEqual(self._akun(702).name, 'Bahan Listrik (revisi)')
        self.assertEqual(len(self._akun(702)), 1)

    def test_v1_kode_sama_di_dua_unit(self):
        report = self.Loader.load_accounts([
            self._acc(711, '6010.240', 'Unit A'),
            self._acc(712, '6010.240', 'Unit B', company=self.code_b),
        ])
        self.assertEqual((report['created'], report['rejected']), (2, []))
        self.assertEqual(self._akun(712, self.company_b)._pkat_code(), '6010.240')

    def test_v5_baris_ditolak_bukan_ditebak(self):
        report = self.Loader.load_accounts([
            self._acc(721, '6010.240', 'Baik'),
            self._acc(722, '6010.241', 'Tipe tak dikenal', 'modul_lain.tipe_aneh'),
            self._acc(723, '6399.400 (copy)', 'Kode berspasi'),
            self._acc(724, '6010.240', 'Kode dobel'),
            self._acc(725, '6010.242', 'Unit tidak ada', company='ZZ'),
        ])
        self.assertEqual(report['created'], 1)
        alasan = {row['id']: reason for row, reason in report['rejected']}
        self.assertEqual(set(alasan), {'722', '723', '724', '725'})
        self.assertIn('tabel pemetaan', alasan['722'])
        self.assertIn('tidak diterima Odoo 20', alasan['723'])
        self.assertIn('dobel', alasan['724'])
        self.assertFalse(self._akun(722))

    def test_v3_induk_tidak_pernah_kas_dan_unpostable(self):
        report = self.Loader.load_accounts([
            self._acc(731, '1100', 'KAS DAN BANK', VIEW),
            self._acc(732, '1100.200', 'Kas', 'liquidity', parent=731),
            self._acc(733, '1100.201', 'Bank', 'liquidity', parent=731),
            self._acc(734, '9999.200', 'Un-postable', UNPOSTABLE),
            self._acc(735, '50', 'BIAYA', VIEW),
            self._acc(736, '5010', 'ST A', VIEW, parent=735),
            self._acc(737, '5010.240', 'Detail', 'expenses', parent=736),
        ])
        self.assertEqual(report['rejected'], [])
        self.assertEqual(self._akun(731).account_type, 'off_balance', "anak hanya kas -> tidak ditiru")
        self.assertTrue(self._akun(734).pkat_is_view)
        self.assertEqual(self._akun(735).account_type, 'expense', "tipe diambil dari cucu")
        self.assertEqual({r['id'] for r in report['view_fallback']}, {'731', '734'})

    def test_v10_daftar_selisih_upah(self):
        report = self.Loader.load_accounts([
            self._acc(741, '5022.4031', 'Upah kode 9 karakter', upah='non_upah'),  # Odoo 10 keliru
            self._acc(742, '5022.403', 'Upah kode 8 karakter', upah='upah'),
            self._acc(743, '5022.440', 'Bahan', upah='non_upah'),
        ])
        self.assertEqual(report['wage_diff'], [{
            'code': '5022.4031', 'name': 'Upah kode 9 karakter', 'company_code': self.code_a,
            'odoo10': 'non_upah', 'odoo20': 'upah'}])
        self.assertEqual(self._akun(741).pkat_wage_type, 'upah')

    # ------------------------------------------------------------- barang
    def _prod(self, id_, code, name, uom_id=110, uom_name='buah', active='t'):
        return {'tmpl_id': str(id_), 'product_id': str(id_), 'default_code': code, 'name': name,
                'uom_id': str(uom_id), 'uom_name': uom_name, 'active': active}

    def test_v6_barang_menunggu_padanan_satuan(self):
        rows = [self._prod(601, '3637.010', 'Bearing 6205'),
                self._prod(602, '3011.001', 'Cat Hitam', uom_id=322, uom_name='kg'),
                self._prod(603, '', 'Tanpa kode'),
                self._prod(604, '3637.010', 'Kode dobel')]
        report = self.Loader.load_products(rows)
        self.assertEqual(report['created'], 0)
        self.assertEqual(len(report['rejected']), 4)
        self.assertIn('belum punya padanan', report['rejected'][0][1])
        # setelah padanan 'buah' disetujui, hanya barang bersatuan itu yang dimuat
        unit = self.env.ref('uom.product_uom_unit')
        self.env['pkat.uom.map'].create({'ka10_id': 110, 'name': 'buah', 'uom_id': unit.id})
        report = self.Loader.load_products(rows)
        self.assertEqual(report['created'], 1)
        alasan = {row['tmpl_id']: reason for row, reason in report['rejected']}
        self.assertEqual(set(alasan), {'602', '603', '604'})
        self.assertIn('dobel', alasan['604'])
        product = self.env['product.product']._pkat_find(['3637.010'])['3637.010']
        self.assertEqual((product.uom_id, product.product_tmpl_id.ka10_id), (unit, 601))
        self.assertEqual(self.Loader.load_products(rows)['created'], 0, "idempoten")

    def test_v6_laporan_satuan_tidak_membuat_apa_pun(self):
        before = self.env['uom.uom'].with_context(active_test=False).search_count([])
        self.env['pkat.uom.map'].create(
            {'ka10_id': 110, 'name': 'buah', 'uom_id': self.env.ref('uom.product_uom_unit').id})
        laporan = self.Loader.uom_report([
            {'id': '110', 'name': 'buah', 'category': 'Unit', 'product_count': '17191'},
            {'id': '135', 'name': 'set', 'category': 'set', 'product_count': '1854'},
            {'id': '999', 'name': 'tidak dipakai', 'category': 'x', 'product_count': '0'},
        ])
        self.assertEqual([u['name'] for u in laporan], ['buah', 'set'])
        self.assertTrue(laporan[0]['mapped'])
        self.assertFalse(laporan[1]['mapped'])
        self.assertEqual(self.env['uom.uom'].with_context(active_test=False).search_count([]), before)
        self.assertEqual(self.env['pkat.uom.map'].search_count([]), 1)
