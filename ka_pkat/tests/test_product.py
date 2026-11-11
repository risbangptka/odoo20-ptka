"""K2/V6: master barang = product.product, kunci default_code."""
from psycopg2 import IntegrityError

from odoo.tests import tagged
from odoo.tools import mute_logger

from .common import PkatCase


@tagged('post_install', '-at_install')
class TestProduct(PkatCase):

    def _barang(self, code, name, **kw):
        vals = {'default_code': code, 'name': name}
        vals.update(kw)
        return self.env['product.template']._pkat_create([vals])

    def test_barang_pkat(self):
        tmpl = self._barang('3637.010', 'Bearing 6205')
        self.assertTrue(tmpl.pkat_managed)
        self.assertFalse(tmpl.company_id, "barang dipakai bersama semua unit")
        product = tmpl.product_variant_id
        self.assertEqual(product._name, 'product.product')
        self.assertTrue(product.pkat_managed)
        self.assertEqual(product.default_code, '3637.010')
        self.assertTrue(product.uom_id)
        found = self.env['product.product']._pkat_find(['3637.010', '0000.000'])
        self.assertEqual(found, {'3637.010': product})

    def test_kode_bertitik_tidak_disamakan(self):
        """3637.010 dan 3637.01 adalah dua kode berbeda (kode disimpan sebagai teks)."""
        a = self._barang('3637.010', 'A')
        b = self._barang('3637.01', 'B')
        found = self.env['product.product']._pkat_find(['3637.010'])
        self.assertEqual(found['3637.010'], a.product_variant_id)
        self.assertNotEqual(a, b)

    def test_v6_kode_unik_di_antara_barang_pkat(self):
        self._barang('3637.010', 'Bearing 6205')
        with self.assertRaises(IntegrityError), mute_logger('odoo.sql_db'):
            self._barang('3637.010', 'Dobel')
            self.env.flush_all()

    def test_v6_barang_bukan_pkat_tidak_dibatasi(self):
        self._barang('3637.010', 'Bearing 6205')
        lain = self.env['product.template'].create({'default_code': '3637.010', 'name': 'Bukan PKAT'})
        self.assertFalse(lain.pkat_managed)
        self.assertNotIn(lain.product_variant_id,
                         self.env['product.product']._pkat_find(['3637.010']).values())

    def test_barang_diarsipkan_tetap_ditemukan_bila_diminta(self):
        tmpl = self._barang('3637.011', 'Arsip')
        tmpl.active = False
        self.assertFalse(self.env['product.product']._pkat_find(['3637.011']))
        self.assertTrue(self.env['product.product']._pkat_find(['3637.011'], active_test=False))
