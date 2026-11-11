from odoo import api, fields, models

from .pkat_config import POCKET_LEVELS
from .pkat_master import WAGE_TYPES


class PkatPocket(models.Model):
    """DM-07. Kantung: batas penguncian. Disimpan sebagai tabel supaya barisnya
    bisa dikunci (SELECT ... FOR UPDATE) saat pemeriksaan (SRS FS-CK-12)."""
    _name = 'pkat.pocket'
    _description = 'Kantung Anggaran'
    _order = 'company_id, year desc, level, wage_type'

    company_id = fields.Many2one('res.company', string='Unit/PG', required=True, index=True)
    currency_id = fields.Many2one(related='company_id.currency_id')
    year = fields.Integer('Tahun', required=True, index=True)
    level = fields.Selection(POCKET_LEVELS, 'Tingkat', required=True)
    ref_account_id = fields.Many2one('pkat.account', 'Perkiraan')
    ref_cost_center_id = fields.Many2one('pkat.cost.center', 'Stasiun')
    ref_department_id = fields.Many2one('pkat.department', 'Bagian')
    wage_type = fields.Selection(WAGE_TYPES, 'Jenis', required=True)
    amount_current = fields.Monetary('Anggaran Berlaku', readonly=True)
    commitment = fields.Monetary('Serapan', readonly=True)
    realization = fields.Monetary('Realisasi', readonly=True)
    pct_commitment = fields.Float('% Serapan', compute='_compute_pct', store=True)
    pct_realization = fields.Float('% Realisasi', compute='_compute_pct', store=True)
    locked_po = fields.Boolean('Terkunci PO', readonly=True)
    locked_real = fields.Boolean('Terkunci Realisasi', readonly=True)
    manual_lock = fields.Boolean('Kunci Manual')
    manual_lock_reason = fields.Text('Alasan Kunci Manual')

    @api.depends('level', 'ref_account_id', 'ref_cost_center_id', 'ref_department_id', 'wage_type', 'year')
    def _compute_display_name(self):
        labels = dict(WAGE_TYPES)
        for rec in self:
            ref = rec.ref_account_id or rec.ref_cost_center_id or rec.ref_department_id
            rec.display_name = '%s (%s) %s' % (
                ref.display_name or '', labels.get(rec.wage_type, ''), rec.year or '')

    @api.depends('amount_current', 'commitment', 'realization')
    def _compute_pct(self):
        for rec in self:
            budget = rec.amount_current
            rec.pct_commitment = rec.commitment / budget * 100 if budget else 0.0
            rec.pct_realization = rec.realization / budget * 100 if budget else 0.0

    # ------------------------------------------------------------------
    # TODO(SRS DM-07, FS-CK-04): implementasi
    # ------------------------------------------------------------------
    @api.model
    def _rebuild_for_configs(self, configs):
        """Bangun ulang kantung setelah pocket_level/lock_basis berubah."""

    @api.model
    def _rebuild_for_budgets(self, budgets):
        """Buat/perbarui kantung setelah PKAT stasiun disetujui."""

    @api.model
    def _find_for_line(self, budget_line):
        """Kantung milik sebuah pkat.budget.line menurut pocket_level config."""
        return self.browse()

    def _lock_rows(self):
        """Kunci baris untuk transaksi ini, urut id (hindari deadlock)."""
        if self:
            self.env.cr.execute(
                'SELECT id FROM pkat_pocket WHERE id IN %s ORDER BY id FOR UPDATE',
                (tuple(self.ids),))
