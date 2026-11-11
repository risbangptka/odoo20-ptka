"""K1/K3/K8 (PERUBAHAN_DESAIN_01): master perkiraan = account.account Odoo 20.

Satu record per unit (V1): company_ids berisi tepat satu company, disalin ke
pkat_company_id supaya bisa dipakai sebagai kunci dan relasi biasa. Sumber data
perkiraan adalah Odoo 10; record PKAT ditandai pkat_managed dan ditautkan lewat ka10_id.

Catatan core Odoo 20: `code` bergantung company (code_store per company root).
Jangan membaca/mencari `code` dengan company aktif sembarang; pakai _pkat_code()
dan _pkat_find().
"""
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
# V4: konteks core yang mencegah jurnal otomatis untuk perkiraan kas/bank dan kartu kredit
# (account.account.create -> _create_default_journals).
NO_JOURNAL_CONTEXT = {'skip_auto_account_journal_creation': True}


class AccountAccount(models.Model):
    _inherit = 'account.account'

    pkat_managed = fields.Boolean(
        'Perkiraan PKAT', index=True, copy=False,
        help="Perkiraan hasil sinkronisasi dari Odoo 10 (K3). Hanya perkiraan ini yang dipakai PKAT.")
    pkat_company_id = fields.Many2one(
        'res.company', 'Unit/PG (PKAT)', compute='_compute_pkat_company_id', store=True, index=True,
        help="V1: satu perkiraan PKAT dimiliki tepat satu Unit/PG.")
    ka10_id = fields.Integer('ID Odoo 10', copy=False, index=True,
                             help="id account.account di Odoo 10, untuk penelusuran.")
    pkat_is_view = fields.Boolean(
        'Perkiraan Induk', copy=False,
        help="K8/V3: perkiraan induk (tipe View) atau Un-Postable di Odoo 10. "
             "Tidak boleh dianggarkan dan tidak membentuk kantung.")
    pkat_cost_center_id = fields.Many2one('pkat.cost.center', 'Stasiun', index=True)
    pkat_department_id = fields.Many2one('hr.department', 'Bagian', index=True)
    pkat_cost_item = fields.Char('Jenis Biaya', size=2, compute='_compute_pkat_cost_item', store=True)
    pkat_wage_type = fields.Selection(WAGE_TYPES, 'Jenis', default='non_upah')
    pkat_kind = fields.Selection(ACCOUNT_KINDS, 'Kelompok', default='expense')
    pkat_unit_pocket = fields.Selection(UNIT_POCKETS, 'Kantung Unit')
    pkat_is_spt = fields.Boolean(
        'Anggaran Tebu SPT',
        help="Tidak dikunci PKAT dan tidak ikut pergeseran (BRD PR-14, SW-05).")
    pkat_needs_completion = fields.Boolean(
        'Perlu Dilengkapi', compute='_compute_pkat_needs_completion', store=True, index=True,
        help="FS-PK-09: perkiraan tanpa stasiun atau bagian harus dilengkapi Bagian Anggaran "
             "sebelum dapat dianggarkan.")

    _pkat_ka10_uniq = models.UniqueIndex(
        '(pkat_company_id, ka10_id) WHERE ka10_id > 0',
        'ID Odoo 10 perkiraan sudah dipakai pada Unit/PG ini.')

    # ------------------------------------------------------------ compute
    @api.depends('company_ids')
    def _compute_pkat_company_id(self):
        for rec in self:
            companies = rec.sudo().company_ids
            rec.pkat_company_id = companies if len(companies) == 1 else False

    def _pkat_code(self):
        """Kode perkiraan menurut Unit/PG pemiliknya, tidak bergantung company aktif."""
        self.ensure_one()
        return self.with_company(self.pkat_company_id or self.env.company).code or ''

    @api.depends('code_store', 'pkat_managed', 'pkat_company_id')
    def _compute_pkat_cost_item(self):
        for rec in self:
            code = rec._pkat_code() if rec.pkat_managed else ''
            rec.pkat_cost_item = code[6:8] if len(code) == ACCOUNT_CODE_LENGTH and code.isdigit() else False

    @api.depends('pkat_managed', 'pkat_is_view', 'pkat_cost_center_id', 'pkat_department_id')
    def _compute_pkat_needs_completion(self):
        for rec in self:
            rec.pkat_needs_completion = bool(
                rec.pkat_managed and not rec.pkat_is_view
                and (not rec.pkat_cost_center_id or not rec.pkat_department_id))

    # --------------------------------------------------------- constraints
    @api.constrains('pkat_managed', 'company_ids')
    def _check_pkat_single_company(self):
        """V1: perkiraan PKAT dimiliki tepat satu Unit/PG."""
        for rec in self:
            if rec.pkat_managed and len(rec.sudo().company_ids) != 1:
                raise ValidationError(_(
                    "Perkiraan PKAT %(acc)s harus dimiliki tepat satu Unit/PG.", acc=rec.display_name))

    @api.constrains('pkat_company_id', 'pkat_cost_center_id', 'pkat_department_id')
    def _check_pkat_company(self):
        """DM-02: perkiraan, stasiun, dan bagiannya harus satu Unit/PG."""
        for rec in self:
            others = rec.pkat_cost_center_id.company_id | rec.pkat_department_id.company_id
            if rec.pkat_managed and others - rec.pkat_company_id:
                raise ValidationError(_(
                    "Stasiun/bagian perkiraan %(acc)s harus dari Unit/PG yang sama.",
                    acc=rec.display_name))

    # -------------------------------------------------------------- cari
    @api.model
    def _pkat_find(self, company, codes, active_test=True):
        """Perkiraan PKAT milik `company` berdasarkan kode -> dict {kode: record}."""
        accounts = self.with_company(company).with_context(active_test=active_test).search([
            ('pkat_managed', '=', True), ('pkat_company_id', '=', company.id),
            ('code', 'in', list(codes))])
        return {acc.code: acc for acc in accounts}

    @api.model
    def _pkat_find_cost_center(self, code, company_id):
        """Stasiun pemilik nomor perkiraan (DM-02).
        Odoo 10 (ka_account) menyimpan kode stasiun sebagai 4 digit pertama perkiraan,
        SRS menyebut digit 3-4; keduanya dicoba, 4 digit pertama didahulukan."""
        code = code or ''
        if len(code) != ACCOUNT_CODE_LENGTH or not code.isdigit() or not company_id:
            return self.env['pkat.cost.center']
        centers = self.env['pkat.cost.center'].search(
            [('company_id', '=', company_id), ('code', 'in', [code[:4], code[2:4]])])
        return (centers.filtered(lambda c: c.code == code[:4]) or centers)[:1]

    def _pkat_fill_owner(self):
        """Stasiun diturunkan dari nomor perkiraan dan bagian dari stasiun bila belum diisi."""
        for rec in self.filtered(lambda a: a.pkat_managed and not a.pkat_is_view):
            if not rec.pkat_cost_center_id:
                rec.pkat_cost_center_id = self._pkat_find_cost_center(
                    rec._pkat_code(), rec.pkat_company_id.id)
            if rec.pkat_cost_center_id and not rec.pkat_department_id:
                rec.pkat_department_id = rec.pkat_cost_center_id.department_id

    @api.onchange('pkat_cost_center_id')
    def _onchange_pkat_cost_center(self):
        if self.pkat_cost_center_id:
            self.pkat_department_id = self.pkat_cost_center_id.department_id

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        records._pkat_fill_owner()
        return records

    @api.model
    def _pkat_create(self, vals_list):
        """Buat perkiraan PKAT tanpa efek samping akuntansi (V4: tanpa jurnal otomatis)."""
        for vals in vals_list:
            vals.setdefault('pkat_managed', True)
        return self.with_context(**NO_JOURNAL_CONTEXT).create(vals_list)
