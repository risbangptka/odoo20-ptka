from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

# Master perkiraan dan bagian memakai model bawaan (PERUBAHAN_DESAIN_01 K1, K7):
# lihat account_account.py dan hr_department.py. Konstanta diekspor ulang dari sini
# supaya impor lama tetap berlaku.
from .account_account import ACCOUNT_KINDS, UNIT_POCKETS, WAGE_TYPES  # noqa: F401


class PkatCostCenter(models.Model):
    """DM-02. Stasiun (pusat biaya); padanan ka_account.stasiun Odoo 10.
    Bagian/seksi/sub seksi menunjuk hr.department (K7)."""
    _name = 'pkat.cost.center'
    _description = 'Stasiun (PKAT)'
    _rec_names_search = ['code', 'name']
    _order = 'company_id, code'

    code = fields.Char('Kode Stasiun', required=True, index=True)
    name = fields.Char('Nama Stasiun', required=True)
    company_id = fields.Many2one('res.company', string='Unit/PG', required=True)
    department_id = fields.Many2one('hr.department', 'Bagian', required=True, index=True)
    section_id = fields.Many2one('hr.department', 'Seksi')
    subsection_id = fields.Many2one('hr.department', 'Sub Seksi')
    ka10_id = fields.Integer('ID Odoo 10', copy=False, index=True,
                             help="id ka_account.stasiun di Odoo 10, untuk penelusuran.")
    active = fields.Boolean(default=True)

    _code_company_uniq = models.Constraint(
        'unique(company_id, code)', 'Kode stasiun harus unik per Unit/PG.')
    _ka10_uniq = models.UniqueIndex(
        '(ka10_id) WHERE ka10_id > 0', 'ID Odoo 10 stasiun sudah dipakai.')

    @api.depends('code', 'name')
    def _compute_display_name(self):
        for rec in self:
            rec.display_name = '%s %s' % (rec.code or '', rec.name or '')

    @api.constrains('company_id', 'department_id', 'section_id', 'subsection_id')
    def _check_company(self):
        """DM-02: stasiun, bagian, seksi, dan sub seksinya harus satu Unit/PG."""
        for rec in self:
            departments = rec.department_id | rec.section_id | rec.subsection_id
            if departments.company_id - rec.company_id:
                raise ValidationError(_(
                    "Bagian/seksi stasiun %(cc)s harus dari Unit/PG yang sama.", cc=rec.display_name))
