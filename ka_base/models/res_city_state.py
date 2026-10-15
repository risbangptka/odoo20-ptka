from odoo import fields, models


class ResCityState(models.Model):
    _name = 'res.city.state'
    _description = 'Kota/Kabupaten'

    name = fields.Char('City Name')
    code = fields.Char('City Code')
    city_state_id = fields.Many2one('res.country.state', string='State')
