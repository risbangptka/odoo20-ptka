from odoo import api, fields, models

WAGE_TYPES = [('upah', 'Tenaga Kerja (Upah)'), ('non_upah', 'Non Tenaga Kerja (Non-Upah)')]
ACCOUNT_KINDS = [('expense', 'Biaya'), ('income', 'Pendapatan'), ('investment', 'Investasi')]
UNIT_POCKETS = [
    ('tenaga_kerja', 'Tenaga Kerja'),
    ('barang_jasa', 'Pemakaian Barang/Jasa'),
    ('bahan_baku_tebu', 'Perolehan Bahan Baku Tebu'),
]


class PkatDepartment(models.Model):
    """DM-02. Bagian/seksi/sub seksi; padanan hr.department Odoo 10 (kunci: code)."""
    _name = 'pkat.department'
    _description = 'Bagian / Seksi (PKAT)'
    _parent_name = 'parent_id'
    _parent_store = True
    _rec_names_search = ['code', 'name']
    _order = 'company_id, code'

    code = fields.Char('Kode', required=True, index=True)
    name = fields.Char('Nama', required=True)
    company_id = fields.Many2one('res.company', string='Unit/PG', required=True)
    parent_id = fields.Many2one('pkat.department', 'Induk', index=True, ondelete='restrict')
    parent_path = fields.Char(index=True)
    manager_user_id = fields.Many2one('res.users', 'Pengguna Anggaran (Kepala)')
    active = fields.Boolean(default=True)

    _code_company_uniq = models.Constraint(
        'unique(company_id, code)', 'Kode bagian harus unik per Unit/PG.')


class PkatCostCenter(models.Model):
    """DM-02. Stasiun (pusat biaya); padanan ka_account.stasiun Odoo 10."""
    _name = 'pkat.cost.center'
    _description = 'Stasiun (PKAT)'
    _rec_names_search = ['code', 'name']
    _order = 'company_id, code'

    code = fields.Char('Kode Stasiun', required=True, index=True)
    name = fields.Char('Nama Stasiun', required=True)
    company_id = fields.Many2one('res.company', string='Unit/PG', required=True)
    department_id = fields.Many2one('pkat.department', 'Bagian', required=True)
    section_id = fields.Many2one('pkat.department', 'Seksi')
    active = fields.Boolean(default=True)

    _code_company_uniq = models.Constraint(
        'unique(company_id, code)', 'Kode stasiun harus unik per Unit/PG.')

    @api.depends('code', 'name')
    def _compute_display_name(self):
        for rec in self:
            rec.display_name = '%s %s' % (rec.code or '', rec.name or '')


class PkatAccount(models.Model):
    """DM-02. Nomor perkiraan 8 digit; padanan account.account Odoo 10.
    Digit 3-4 = stasiun, digit 7-8 = jenis biaya (cost item)."""
    _name = 'pkat.account'
    _description = 'Perkiraan (PKAT)'
    _rec_names_search = ['code', 'name']
    _order = 'company_id, code'

    code = fields.Char('No. Perkiraan', required=True, index=True)
    name = fields.Char('Nama Perkiraan', required=True)
    company_id = fields.Many2one('res.company', string='Unit/PG', required=True)
    cost_center_id = fields.Many2one('pkat.cost.center', 'Stasiun')
    department_id = fields.Many2one('pkat.department', 'Bagian')
    cost_item = fields.Char('Jenis Biaya', size=2, compute='_compute_cost_item', store=True)
    wage_type = fields.Selection(WAGE_TYPES, 'Jenis', default='non_upah', required=True)
    kind = fields.Selection(ACCOUNT_KINDS, 'Kelompok', default='expense', required=True)
    unit_pocket = fields.Selection(UNIT_POCKETS, 'Kantung Unit')
    is_spt = fields.Boolean('Anggaran Tebu SPT',
                            help="Tidak dikunci PKAT dan tidak ikut pergeseran (BRD PR-14, SW-05).")
    active = fields.Boolean(default=True)

    _code_company_uniq = models.Constraint(
        'unique(company_id, code)', 'Nomor perkiraan harus unik per Unit/PG.')

    @api.depends('code')
    def _compute_cost_item(self):
        for rec in self:
            digits = ''.join(ch for ch in (rec.code or '') if ch.isdigit())
            rec.cost_item = digits[6:8] if len(digits) >= 8 else False

    @api.depends('code', 'name')
    def _compute_display_name(self):
        for rec in self:
            rec.display_name = '%s %s' % (rec.code or '', rec.name or '')
