import hashlib
import secrets

from odoo import _, api, fields, models
from odoo.exceptions import UserError

POCKET_LEVELS = [
    ('account', 'Perkiraan'),
    ('cost_center', 'Stasiun'),
    ('department', 'Bagian'),
]
LOCK_BASIS = [
    ('yearly', 'Tahunan (yearly)'),
    ('ytd', 'S.d. bulan berjalan (year to date)'),
    ('mtd', 'Bulan berjalan (month to date)'),
]


class PkatConfig(models.Model):
    """DM-01. Konfigurasi penguncian per company dan tahun anggaran.
    Hanya Bagian Anggaran Kantor Direksi yang boleh mengubah (BRD PR-12, LK-01)."""
    _name = 'pkat.config'
    _description = 'Konfigurasi PKAT'
    _inherit = ['mail.thread']
    _order = 'year desc, company_id'

    company_id = fields.Many2one('res.company', string='Unit/PG', required=True,
                                 default=lambda self: self.env.company)
    year = fields.Integer('Tahun Anggaran', required=True,
                          default=lambda self: fields.Date.today().year)
    pocket_level = fields.Selection(POCKET_LEVELS, 'Tingkat Kantung', required=True,
                                    default='department', tracking=True)
    lock_basis = fields.Selection(LOCK_BASIS, 'Dasar Penguncian', required=True,
                                  default='yearly', tracking=True)
    ews_yellow = fields.Float('Ambang Kuning (%)', default=75.0, tracking=True)
    ews_red = fields.Float('Ambang Merah (%)', default=100.0, tracking=True)
    sync_stale_minutes = fields.Integer('Batas Sinkron Basi (menit)', default=60)
    lock_active = fields.Boolean('Penguncian Aktif', default=True, tracking=True)

    # Odoo 20: models.Constraint menggantikan _sql_constraints (terverifikasi di core,
    # odoo/orm/table_objects.py); nama di DB: pkat_config_company_year_uniq.
    _company_year_uniq = models.Constraint(
        'unique(company_id, year)',
        'Konfigurasi PKAT sudah ada untuk Unit/PG dan tahun ini.')

    @api.depends('company_id', 'year')
    def _compute_display_name(self):
        for rec in self:
            rec.display_name = '%s - %s' % (rec.company_id.display_name or '', rec.year or '')

    @api.model
    def get_for(self, company, year):
        """Konfigurasi untuk company+tahun; UserError jelas bila belum dibuat."""
        config = self.search([('company_id', '=', company.id), ('year', '=', year)], limit=1)
        if not config:
            raise UserError(_(
                "Konfigurasi PKAT untuk %(company)s tahun %(year)s belum dibuat.",
                company=company.display_name, year=year))
        return config

    def write(self, vals):
        res = super().write(vals)
        if {'pocket_level', 'lock_basis'} & set(vals):
            # TODO(SRS DM-01): bangun ulang pkat.pocket untuk company+tahun ini.
            self.env['pkat.pocket']._rebuild_for_configs(self)
        return res


class PkatApiToken(models.Model):
    """Token API per company (SRS API-G-02/03). Token asli hanya tampil sekali
    saat dibuat; yang disimpan hanya hash SHA-256."""
    _name = 'pkat.api.token'
    _description = 'Token API PKAT'

    name = fields.Char('Keterangan', required=True)
    company_id = fields.Many2one('res.company', string='Unit/PG', required=True)
    token_hash = fields.Char('Hash Token', readonly=True, copy=False)
    active = fields.Boolean(default=True)
    last_used = fields.Datetime('Terakhir Dipakai', readonly=True)

    @staticmethod
    def _hash(token):
        return hashlib.sha256((token or '').encode('utf-8')).hexdigest()

    def action_generate(self):
        """Buat token baru dan tampilkan SEKALI kepada admin."""
        self.ensure_one()
        token = secrets.token_urlsafe(32)
        self.token_hash = self._hash(token)
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Token API baru (salin sekarang, tidak ditampilkan lagi)'),
                'message': token,
                'sticky': True,
            },
        }

    @api.model
    def _authenticate(self, company_code, token):
        """Kembalikan record token yang cocok, atau recordset kosong."""
        if not company_code or not token:
            return self.browse()
        rec = self.sudo().search([
            ('company_id.code', '=', company_code),
            ('token_hash', '=', self._hash(token)),
        ], limit=1)
        if rec:
            rec.last_used = fields.Datetime.now()
        return rec
