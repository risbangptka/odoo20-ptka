from odoo import api, fields, models


class ResUsers(models.Model):
    _inherit = 'res.users'

    # Override default groups_id dari Odoo 10 dihapus: Odoo 20 sudah mengambil
    # grup default dari base.default_user_group (lihat res.users._default_groups).

    default_operating_unit_id = fields.Many2one('res.partner', 'Default Unit/PG', compute='_compute_operating_unit', store=True)
    # relation/column dikunci ke nama tabel Odoo 10 agar data hasil migrasi terbaca
    operating_unit_ids = fields.Many2many(
        'res.partner', 'res_partner_res_users_rel', 'res_users_id', 'res_partner_id',
        string="Unit/PG", compute='_compute_operating_units', store=True)

    @api.model
    def operating_unit_default_get(self, uid2):
        user = self.env['res.users'].browse(uid2 or self.env.uid)
        return user.default_operating_unit_id

    @api.depends('company_id')
    def _compute_operating_unit(self):
        for user in self:
            user.default_operating_unit_id = user.company_id.partner_id

    @api.depends('company_ids')
    def _compute_operating_units(self):
        for user in self:
            user.operating_unit_ids = user.company_ids.partner_id
