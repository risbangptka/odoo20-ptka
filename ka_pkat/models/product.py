"""K2/K3/V6 (PERUBAHAN_DESAIN_01): master barang = product.product Odoo 20.

Sumber data barang adalah Odoo 10; kunci tautan `default_code` (di Odoo 10 unik lintas
company). Barang PKAT ditandai pkat_managed dan tidak dimiliki company tertentu.
Hanya masternya yang dipakai: tidak ada transaksi stok di Odoo 20 (bagian 4).
"""
from odoo import api, fields, models


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    pkat_managed = fields.Boolean(
        'Barang PKAT', index=True, copy=False,
        help="Barang hasil sinkronisasi dari Odoo 10 (K3).")
    ka10_id = fields.Integer('ID Odoo 10', copy=False, index=True,
                             help="id product.template di Odoo 10, untuk penelusuran.")

    # V6: default_code unik di antara barang pkat_managed (barang lain tidak dibatasi)
    _pkat_default_code_uniq = models.UniqueIndex(
        '(default_code) WHERE pkat_managed IS TRUE',
        'Kode barang PKAT tidak boleh dobel.')
    _pkat_ka10_uniq = models.UniqueIndex(
        '(ka10_id) WHERE ka10_id > 0', 'ID Odoo 10 barang sudah dipakai.')

    @api.model
    def _pkat_create(self, vals_list):
        """Buat barang PKAT: dipakai bersama semua unit (company kosong), kode wajib."""
        for vals in vals_list:
            vals.setdefault('pkat_managed', True)
            vals.setdefault('company_id', False)
        return self.create(vals_list)


class ProductProduct(models.Model):
    _inherit = 'product.product'

    pkat_managed = fields.Boolean(related='product_tmpl_id.pkat_managed', store=True, index=True)

    @api.model
    def _pkat_find(self, codes, active_test=True):
        """Barang PKAT berdasarkan kode -> dict {default_code: record}."""
        products = self.with_context(active_test=active_test).search(
            [('pkat_managed', '=', True), ('default_code', 'in', list(codes))])
        return {product.default_code: product for product in products}
