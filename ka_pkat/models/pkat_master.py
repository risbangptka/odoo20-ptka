from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

WAGE_TYPES = [('upah', 'Tenaga Kerja (Upah)'), ('non_upah', 'Non Tenaga Kerja (Non-Upah)')]
ACCOUNT_KINDS = [('expense', 'Biaya'), ('income', 'Pendapatan'), ('investment', 'Investasi')]
UNIT_POCKETS = [
    ('tenaga_kerja', 'Tenaga Kerja'),
    ('barang_jasa', 'Pemakaian Barang/Jasa'),
    ('bahan_baku_tebu', 'Perolehan Bahan Baku Tebu'),
]
ACCOUNT_CODE_LENGTH = 8


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

    @api.constrains('parent_id', 'company_id')
    def _check_parent(self):
        """DM-02: hierarki tidak lintas Unit/PG (lingkaran sudah ditolak core lewat _parent_store)."""
        for rec in self:
            if rec.parent_id and rec.parent_id.company_id != rec.company_id:
                raise ValidationError(_(
                    "Induk bagian %(dept)s harus dari Unit/PG yang sama.", dept=rec.display_name))


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

    @api.constrains('company_id', 'department_id', 'section_id')
    def _check_company(self):
        """DM-02: stasiun, bagian, dan seksinya harus satu Unit/PG."""
        for rec in self:
            if (rec.department_id | rec.section_id).company_id - rec.company_id:
                raise ValidationError(_(
                    "Bagian/seksi stasiun %(cc)s harus dari Unit/PG yang sama.", cc=rec.display_name))


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
    needs_completion = fields.Boolean(
        'Perlu Dilengkapi', compute='_compute_needs_completion', store=True, index=True,
        help="FS-PK-09: perkiraan tanpa stasiun atau bagian harus dilengkapi Bagian Anggaran "
             "sebelum dapat dianggarkan.")

    _code_company_uniq = models.Constraint(
        'unique(company_id, code)', 'Nomor perkiraan harus unik per Unit/PG.')

    @api.depends('cost_center_id', 'department_id')
    def _compute_needs_completion(self):
        for rec in self:
            rec.needs_completion = not rec.cost_center_id or not rec.department_id

    @api.depends('code')
    def _compute_cost_item(self):
        for rec in self:
            code = rec.code or ''
            rec.cost_item = code[6:8] if len(code) == ACCOUNT_CODE_LENGTH and code.isdigit() else False

    @api.depends('code', 'name')
    def _compute_display_name(self):
        for rec in self:
            rec.display_name = '%s %s' % (rec.code or '', rec.name or '')

    @api.constrains('code')
    def _check_code(self):
        """DM-02: nomor perkiraan tepat 8 digit angka."""
        for rec in self:
            if len(rec.code) != ACCOUNT_CODE_LENGTH or not rec.code.isdigit():
                raise ValidationError(_(
                    "Nomor perkiraan harus %(n)s digit angka: %(code)s",
                    n=ACCOUNT_CODE_LENGTH, code=rec.code))

    @api.constrains('company_id', 'cost_center_id', 'department_id')
    def _check_company(self):
        """DM-02: perkiraan, stasiun, dan bagiannya harus satu Unit/PG."""
        for rec in self:
            if (rec.cost_center_id.company_id | rec.department_id.company_id) - rec.company_id:
                raise ValidationError(_(
                    "Stasiun/bagian perkiraan %(acc)s harus dari Unit/PG yang sama.",
                    acc=rec.display_name))

    @api.model
    def _find_cost_center(self, code, company_id):
        """Stasiun pemilik nomor perkiraan (DM-02: digit 3-4 = stasiun).
        Odoo 10 (ka_account) menyimpan kode stasiun sebagai 4 digit pertama perkiraan,
        SRS menyebut digit 3-4; keduanya dicoba, 4 digit pertama didahulukan."""
        code = code or ''
        if len(code) != ACCOUNT_CODE_LENGTH or not code.isdigit() or not company_id:
            return self.env['pkat.cost.center']
        centers = self.env['pkat.cost.center'].search(
            [('company_id', '=', company_id), ('code', 'in', [code[:4], code[2:4]])])
        return (centers.filtered(lambda c: c.code == code[:4]) or centers)[:1]

    @api.onchange('code', 'company_id')
    def _onchange_code(self):
        if not self.cost_center_id:
            self.cost_center_id = self._find_cost_center(self.code, self.company_id.id)

    @api.onchange('cost_center_id')
    def _onchange_cost_center(self):
        if self.cost_center_id:
            self.department_id = self.cost_center_id.department_id

    @api.model_create_multi
    def create(self, vals_list):
        """Stasiun diturunkan dari nomor perkiraan dan bagian dari stasiun bila tidak diisi."""
        for vals in vals_list:
            if not vals.get('cost_center_id'):
                vals['cost_center_id'] = self._find_cost_center(
                    vals.get('code'), vals.get('company_id')).id
            if vals.get('cost_center_id') and not vals.get('department_id'):
                vals['department_id'] = self.env['pkat.cost.center'].browse(
                    vals['cost_center_id']).department_id.id
        return super().create(vals_list)
