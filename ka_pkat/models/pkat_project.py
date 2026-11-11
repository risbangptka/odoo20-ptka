from odoo import _, api, fields, models
from odoo.exceptions import UserError

PROJECT_TYPES = [
    ('investasi_baru', 'Investasi Baru'),
    ('plb', 'Perbaikan Luar Biasa'),
    ('inventaris', 'Inventaris'),
    ('penggantian', 'Penggantian'),
    ('memorandum', 'Memorandum'),
    ('rutin', 'Rutin'),
]
PROJECT_STATES = [
    ('draft', 'Draft'),
    ('pengajuan', 'Pengajuan'),
    ('approved', 'Disetujui'),
    ('closed', 'Selesai'),
    ('cancel', 'Dibatalkan'),
]


class PkatProject(models.Model):
    """DM-06. Nomor Investasi (padanan logistik.pkrat Odoo 10)."""
    _name = 'pkat.project'
    _description = 'Nomor Investasi'
    _inherit = ['mail.thread']
    _rec_names_search = ['code', 'name']
    _order = 'code desc'

    code = fields.Char('No. Proyek', required=True, index=True, tracking=True)
    name = fields.Char('Nama Proyek', required=True, tracking=True)
    specification = fields.Text('Spesifikasi')
    project_type = fields.Selection(PROJECT_TYPES, 'Jenis', required=True, tracking=True)
    company_id = fields.Many2one('res.company', string='Unit/PG', required=True,
                                 default=lambda self: self.env.company)
    currency_id = fields.Many2one(related='company_id.currency_id')
    cost_center_id = fields.Many2one('pkat.cost.center', 'Stasiun')
    department_id = fields.Many2one(related='cost_center_id.department_id', store=True)
    expense_account_id = fields.Many2one(
        'account.account', 'Perkiraan Biaya Rutin (PLB)',
        help="Khusus PLB: PO PLB juga menambah serapan perkiraan ini (BRD SR-09).")
    amount_total = fields.Monetary('Nilai Proyek (PKAT)', tracking=True)
    year_ids = fields.One2many('pkat.project.year', 'project_id', 'Alokasi per Tahun')
    commitment = fields.Monetary('Serapan', readonly=True)
    realization = fields.Monetary('Realisasi', readonly=True)
    physical_pct = fields.Float('Realisasi Fisik (%)', tracking=True,
                                help="Input manual berdasarkan progres lapangan (BRD BR-03).")
    state = fields.Selection(PROJECT_STATES, 'Status', default='draft', required=True, tracking=True)
    closed_date = fields.Date('Tanggal Tutup', readonly=True)

    _code_company_uniq = models.Constraint(
        'unique(company_id, code)', 'Nomor proyek harus unik per Unit/PG.')

    @api.depends('code', 'name')
    def _compute_display_name(self):
        for rec in self:
            rec.display_name = '%s %s' % (rec.code or '', rec.name or '')

    def action_approve(self):
        self.write({'state': 'approved'})

    def action_close(self):
        """SRS FS-IV-01: proyek ditutup tidak menerima transaksi baru."""
        self.write({'state': 'closed', 'closed_date': fields.Date.today()})

    def action_carry_over(self):
        """SRS FS-PK-08: salin sisa ke tahun berikutnya. TODO implementasi."""
        raise UserError(_("Carry over belum diimplementasikan."))


class PkatProjectYear(models.Model):
    """Alokasi Nomor Investasi per tahun + rencana bulanan (BRD PK-07, PK-14)."""
    _name = 'pkat.project.year'
    _description = 'Alokasi Tahunan Nomor Investasi'
    _order = 'project_id, year'

    project_id = fields.Many2one('pkat.project', 'Nomor Investasi', required=True, ondelete='cascade')
    company_id = fields.Many2one(related='project_id.company_id', store=True)
    currency_id = fields.Many2one(related='company_id.currency_id')
    year = fields.Integer('Tahun', required=True)
    amount_allocated = fields.Monetary('Alokasi PKAT')
    amount_carry_over = fields.Monetary('Carry Over')
    amount_added = fields.Monetary('Tambahan', readonly=True)
    amount_current = fields.Monetary('Anggaran Berlaku', compute='_compute_current', store=True)
    # rencana bulanan disimpan sebagai 12 kolom agar ringkas; boleh dipecah jadi model bila perlu
    plan_01 = fields.Monetary('Jan'); plan_02 = fields.Monetary('Feb'); plan_03 = fields.Monetary('Mar')
    plan_04 = fields.Monetary('Apr'); plan_05 = fields.Monetary('Mei'); plan_06 = fields.Monetary('Jun')
    plan_07 = fields.Monetary('Jul'); plan_08 = fields.Monetary('Agu'); plan_09 = fields.Monetary('Sep')
    plan_10 = fields.Monetary('Okt'); plan_11 = fields.Monetary('Nov'); plan_12 = fields.Monetary('Des')
    commitment = fields.Monetary('Serapan', readonly=True)
    realization = fields.Monetary('Realisasi', readonly=True)

    _project_year_uniq = models.Constraint(
        'unique(project_id, year)', 'Alokasi tahun ini sudah ada untuk proyek tersebut.')

    @api.depends('amount_allocated', 'amount_carry_over', 'amount_added')
    def _compute_current(self):
        for rec in self:
            rec.amount_current = rec.amount_allocated + rec.amount_carry_over + rec.amount_added

    def monthly_plan(self):
        self.ensure_one()
        return [self['plan_%02d' % m] for m in range(1, 13)]
