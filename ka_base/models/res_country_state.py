from odoo import fields, models


class ResCountryState(models.Model):
    _inherit = 'res.country.state'

    active = fields.Boolean(string="Active", default=True, help="If unchecked, it will allow you to hide the Country State without removing it.")
