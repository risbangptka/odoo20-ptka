"""K7/V9 (PERUBAHAN_DESAIN_01): bagian/seksi/sub seksi = hr.department Odoo 20."""
from odoo import fields, models


class HrDepartment(models.Model):
    _inherit = 'hr.department'

    pkat_code = fields.Char(
        'Kode Bagian (PKAT)', index=True,
        help="V9: kode bagian dari ka_account.bagian Odoo 10.")
    pkat_manager_user_id = fields.Many2one(
        'res.users', 'Pengguna Anggaran (Kepala)',
        help="AK-02: pengguna yang berhak melihat anggaran departemen ini beserta turunannya. "
             "Satu penanggung jawab per departemen; diisi manual sampai sinkronisasi master "
             "(API-08) tersedia, karena master pegawai belum ada di Odoo 20.")
    ka10_id = fields.Integer('ID Odoo 10', copy=False, index=True,
                             help="id hr.department di Odoo 10, untuk penelusuran.")

    _pkat_ka10_uniq = models.UniqueIndex(
        '(ka10_id) WHERE ka10_id > 0', 'ID Odoo 10 departemen sudah dipakai.')
