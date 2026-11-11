from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.tools import float_compare

BUDGET_STATES = [
    ('draft', 'Draft'),
    ('proses', 'Proses'),
    ('pengajuan', 'Pengajuan'),
    ('penyesuaian', 'Penyesuaian'),
    ('proses_direksi', 'Proses Direksi'),
    ('approved', 'Disetujui Direksi'),
    ('cancel', 'Dibatalkan'),
]
EWS_COLORS = [('green', 'Hijau'), ('yellow', 'Kuning'), ('red', 'Merah')]


class PkatBudget(models.Model):
    """DM-03. PKAT per stasiun per tahun (padanan logistik.pkrat.stasiun)."""
    _name = 'pkat.budget'
    _description = 'PKAT Stasiun'
    _inherit = ['mail.thread']
    _order = 'year desc, cost_center_id'

    cost_center_id = fields.Many2one('pkat.cost.center', 'Stasiun', required=True, tracking=True)
    department_id = fields.Many2one(related='cost_center_id.department_id', store=True)
    company_id = fields.Many2one(related='cost_center_id.company_id', store=True)
    currency_id = fields.Many2one(related='company_id.currency_id')
    year = fields.Integer('Tahun Anggaran', required=True, tracking=True,
                          default=lambda self: fields.Date.today().year + 1)
    state = fields.Selection(BUDGET_STATES, 'Status', default='draft', required=True, tracking=True)
    line_ids = fields.One2many('pkat.budget.line', 'budget_id', 'Perkiraan')
    amount_current = fields.Monetary('Anggaran Berlaku', compute='_compute_totals', store=True)
    commitment = fields.Monetary('Serapan', compute='_compute_totals', store=True)
    realization = fields.Monetary('Realisasi', compute='_compute_totals', store=True)

    _cost_center_year_uniq = models.Constraint(
        'unique(cost_center_id, year)', 'PKAT stasiun untuk tahun ini sudah ada.')

    @api.depends('cost_center_id', 'year')
    def _compute_display_name(self):
        for rec in self:
            rec.display_name = '%s - %s' % (rec.cost_center_id.display_name or '', rec.year or '')

    @api.depends('line_ids.amount_current', 'line_ids.commitment', 'line_ids.realization')
    def _compute_totals(self):
        for rec in self:
            rec.amount_current = sum(rec.line_ids.mapped('amount_current'))
            rec.commitment = sum(rec.line_ids.mapped('commitment'))
            rec.realization = sum(rec.line_ids.mapped('realization'))

    # --- alur status (SRS FS-PK-03) ---
    def _set_state(self, state):
        self.write({'state': state})

    def action_proses(self):
        self._set_state('proses')

    def action_ajukan(self):
        for rec in self:
            rec.line_ids._check_monthly_total(strict=True)
        self._set_state('pengajuan')

    def action_penyesuaian(self):
        self._set_state('penyesuaian')

    def action_proses_direksi(self):
        self._set_state('proses_direksi')

    def action_approve(self):
        for rec in self:
            rec.line_ids._check_monthly_total(strict=True)
        self._set_state('approved')
        self.env['pkat.pocket']._rebuild_for_budgets(self)

    def action_cancel(self):
        if any(rec.state == 'approved' for rec in self):
            raise UserError(_("PKAT yang sudah disetujui tidak dapat dibatalkan."))
        self._set_state('cancel')


class PkatBudgetLine(models.Model):
    """DM-04. Anggaran per perkiraan (padanan logistik.pkrat.account)."""
    _name = 'pkat.budget.line'
    _description = 'Anggaran per Perkiraan'
    _order = 'budget_id, account_id'

    budget_id = fields.Many2one('pkat.budget', 'PKAT Stasiun', required=True, ondelete='cascade')
    account_id = fields.Many2one(
        'account.account', 'Perkiraan', required=True, index=True,
        # K1/K8/FS-PK-09: hanya perkiraan PKAT detail yang lengkap, milik stasiun PKAT ini
        domain="[('pkat_managed', '=', True), ('pkat_is_view', '=', False), "
               "('pkat_needs_completion', '=', False), ('pkat_cost_center_id', '=', cost_center_id)]")
    company_id = fields.Many2one(related='budget_id.company_id', store=True)
    currency_id = fields.Many2one(related='company_id.currency_id')
    year = fields.Integer(related='budget_id.year', store=True)
    state = fields.Selection(related='budget_id.state', store=True)
    cost_center_id = fields.Many2one(related='budget_id.cost_center_id', store=True)
    department_id = fields.Many2one(related='budget_id.department_id', store=True)
    wage_type = fields.Selection(related='account_id.pkat_wage_type', store=True)

    amount_goods = fields.Monetary('Barang')
    amount_nongoods = fields.Monetary('Non Barang')
    amount_wage = fields.Monetary('Tenaga Kerja')
    amount_project = fields.Monetary('Proyek')
    amount_initial = fields.Monetary('Anggaran Awal', compute='_compute_amounts', store=True)
    # diisi oleh pkat.change.request saat diproses (jangan diedit manual)
    shift_in = fields.Monetary('Geser Masuk', readonly=True)
    shift_out = fields.Monetary('Geser Keluar', readonly=True)
    amount_added = fields.Monetary('Tambahan', readonly=True)
    amount_current = fields.Monetary('Anggaran Berlaku', compute='_compute_amounts', store=True)

    # agregat buku; ditulis oleh pkat.commitment / pkat.realization dalam transaksi yang sama
    commitment = fields.Monetary('Serapan', readonly=True)
    realization = fields.Monetary('Realisasi', readonly=True)
    remain_commitment = fields.Monetary('Sisa Serapan', compute='_compute_position', store=True)
    remain_budget = fields.Monetary('Sisa Anggaran', compute='_compute_position', store=True)
    pct_commitment = fields.Float('% Serapan', compute='_compute_position', store=True)
    pct_realization = fields.Float('% Realisasi', compute='_compute_position', store=True)
    ews_color = fields.Selection(EWS_COLORS, 'EWS', compute='_compute_position', store=True)
    month_ids = fields.One2many('pkat.budget.month', 'line_id', 'Rencana Bulanan')

    _budget_account_uniq = models.Constraint(
        'unique(budget_id, account_id)', 'Perkiraan sudah ada pada PKAT stasiun ini.')

    @api.constrains('account_id', 'budget_id')
    def _check_account(self):
        """K1/K8/FS-PK-09: hanya perkiraan PKAT detail yang sudah lengkap yang dapat dianggarkan."""
        for rec in self:
            account = rec.account_id
            if not account.pkat_managed or account.pkat_company_id != rec.company_id:
                raise ValidationError(_(
                    "Perkiraan %(acc)s bukan perkiraan PKAT milik %(company)s.",
                    acc=account.display_name, company=rec.company_id.display_name))
            if account.pkat_is_view:
                raise ValidationError(_(
                    "Perkiraan induk %(acc)s tidak dapat dianggarkan.", acc=account.display_name))
            if account.pkat_needs_completion:
                raise ValidationError(_(
                    "Perkiraan %(acc)s belum punya stasiun atau bagian. "
                    "Lengkapi master perkiraan sebelum dianggarkan.",
                    acc=rec.account_id.display_name))
            if account.pkat_cost_center_id != rec.budget_id.cost_center_id:
                raise ValidationError(_(
                    "Perkiraan %(acc)s milik stasiun %(own)s, bukan stasiun %(cc)s.",
                    acc=account.display_name, own=account.pkat_cost_center_id.display_name,
                    cc=rec.budget_id.cost_center_id.display_name))

    @api.depends('amount_goods', 'amount_nongoods', 'amount_wage', 'amount_project',
                 'shift_in', 'shift_out', 'amount_added')
    def _compute_amounts(self):
        for rec in self:
            rec.amount_initial = (rec.amount_goods + rec.amount_nongoods
                                  + rec.amount_wage + rec.amount_project)
            rec.amount_current = (rec.amount_initial + rec.shift_in
                                  - rec.shift_out + rec.amount_added)

    @api.depends('amount_current', 'commitment', 'realization')
    def _compute_position(self):
        for rec in self:
            budget = rec.amount_current
            rec.remain_commitment = budget - rec.commitment
            rec.remain_budget = budget - rec.realization
            rec.pct_commitment = rec.commitment / budget * 100 if budget else 0.0
            rec.pct_realization = rec.realization / budget * 100 if budget else 0.0
            rec.ews_color = rec._ews_color(rec.pct_commitment)

    def _ews_color(self, pct):
        """SRS FS-EW-01. Ambang dari pkat.config; bawaan 75/100."""
        self.ensure_one()
        config = self.env['pkat.config'].search(
            [('company_id', '=', self.company_id.id), ('year', '=', self.year)], limit=1)
        yellow = config.ews_yellow if config else 75.0
        red = config.ews_red if config else 100.0
        if pct > red:
            return 'red'
        if pct > yellow:
            return 'yellow'
        return 'green'

    def _check_monthly_total(self, strict=False):
        """BRD PK-03: total bulanan = total tahunan. strict=True -> ValidationError."""
        bad = self.filtered(lambda l: l.month_ids and float_compare(
            sum(l.month_ids.mapped('amount_plan')), l.amount_current, precision_digits=2))
        if bad and strict:
            raise ValidationError(_(
                "Total rencana bulanan belum sama dengan anggaran tahunan pada: %s",
                ', '.join(bad.mapped('account_id.display_name'))))
        return bad

    def write(self, vals):
        locked = {'amount_goods', 'amount_nongoods', 'amount_wage', 'amount_project', 'account_id'}
        if locked & set(vals) and any(l.state == 'approved' for l in self):
            # BRD PK-06 / SRS FS-PK-04
            raise UserError(_(
                "Anggaran yang sudah disetujui tidak dapat diedit. "
                "Gunakan permohonan pergeseran atau tambahan."))
        return super().write(vals)


class PkatBudgetMonth(models.Model):
    """DM-05. Rencana bulanan (padanan logistik.pkrat.bulan)."""
    _name = 'pkat.budget.month'
    _description = 'Rencana Bulanan Perkiraan'
    _order = 'line_id, month'

    line_id = fields.Many2one('pkat.budget.line', 'Perkiraan', required=True, ondelete='cascade')
    company_id = fields.Many2one(related='line_id.company_id', store=True)
    currency_id = fields.Many2one(related='company_id.currency_id')
    month = fields.Integer('Bulan', required=True)
    amount_plan = fields.Monetary('Rencana')
    commitment = fields.Monetary('Serapan', readonly=True)
    realization = fields.Monetary('Realisasi', readonly=True)

    _line_month_uniq = models.Constraint(
        'unique(line_id, month)', 'Bulan sudah ada untuk perkiraan ini.')
    _month_range = models.Constraint(
        'check(month between 1 and 12)', 'Bulan harus 1 sampai 12.')
