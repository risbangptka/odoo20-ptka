from odoo import fields, models


class ResPartner(models.Model):
    _inherit = 'res.partner'

    new_city = fields.Many2one('res.city.state', string='Kota/Kabupaten')
    is_operating_unit = fields.Boolean("Sebagai Unit/PG", default=False)

    def get_company_ref(self):
        """Company yang partner-nya adalah Unit/PG ini.

        Odoo 10 (@api.one) mengembalikan list sehingga pemanggil menulis
        ``get_company_ref()[0]``. Sekarang mengembalikan recordset (maks. 1);
        ``[0]`` masih jalan selama company-nya ada, tapi saat modul pemanggil
        di-port sebaiknya ``[0]`` dibuang.
        """
        self.ensure_one()
        return self.env['res.company'].search([('partner_id', '=', self.id)], limit=1)
