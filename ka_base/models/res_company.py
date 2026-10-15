from odoo import _, api, fields, models
from odoo.exceptions import UserError


class ResCompany(models.Model):
    _inherit = 'res.company'
    # Cari company lewat kode juga (mis. ketik "2" -> PG KEBON AGUNG).
    # Pengganti override name_search Odoo 10.
    _rec_names_search = ['code', 'name']

    # KB-04: dulu default=SUPERUSER_ID, sehingga company baru diam-diam menjalankan
    # semua proses R/K/otomatis sebagai superuser. Sekarang kosong dan wajib diisi;
    # ambil lewat get_*_user() di bawah, yang memberi error jelas bila belum diisi.
    intercompany_user_id = fields.Many2one("res.users", string="User R/K", help="User yang akan melakukan R/K secara otomatis")
    internal_user_id = fields.Many2one("res.users", string="Internal User", help="Internal user for this company")
    automated_system_user_id = fields.Many2one("res.users", string="Automated System", help="Automated user for doing automated task.")
    # KB-07: dulu size=1 (maks. ~10 Unit/PG). Kode lama (0/1/2/4) tidak berubah.
    # Awas: ka_account membentuk kode akun dengan code.replace("U", company.code),
    # jadi kode >1 karakter ikut memperpanjang kode akun company tsb.
    code = fields.Char("Code", size=4)

    @api.depends('name', 'code')
    def _compute_display_name(self):
        # Pengganti name_get Odoo 10: tampil sebagai "code nama".
        super()._compute_display_name()
        for company in self:
            if company.code:
                company.display_name = '%s %s' % (company.code, company.name)

    def _get_ka_system_user(self, field_name):
        self.ensure_one()
        user = self[field_name]
        if not user:
            raise UserError(_(
                "Field '%(field)s' pada company '%(company)s' belum diisi. "
                "Isi dulu di Settings > Companies > %(company)s > tab Setting R/K (mode developer).",
                field=self._fields[field_name].string, company=self.display_name,
            ))
        return user

    def get_intercompany_user(self):
        return self._get_ka_system_user('intercompany_user_id')

    def get_automated_system_user(self):
        return self._get_ka_system_user('automated_system_user_id')

    def get_internal_user(self):
        # Tetap mengembalikan id seperti di Odoo 10 (dipakai ka_account report_financial_custom).
        return self._get_ka_system_user('internal_user_id').id
