from odoo import fields, models


class PkatCheckLog(models.Model):
    """DM-12. Setiap peringatan dan penolakan pemeriksaan anggaran (BRD PR-10)."""
    _name = 'pkat.check.log'
    _description = 'Log Pemeriksaan Anggaran'
    _order = 'id desc'

    company_id = fields.Many2one('res.company', string='Unit/PG', index=True)
    user_login = fields.Char('Pengguna Odoo 10')
    check_kind = fields.Selection([('SPM', 'SPM/SPPJ'), ('PO', 'PO'), ('REALISASI', 'Realisasi')], 'Jenis Cek')
    doc_number = fields.Char('No. Dokumen')
    doc_date = fields.Date('Tanggal Dokumen')
    account_id = fields.Many2one('pkat.account', 'Perkiraan')
    project_id = fields.Many2one('pkat.project', 'Nomor Investasi')
    pocket_id = fields.Many2one('pkat.pocket', 'Kantung')
    limit_amount = fields.Float('Batas')
    used_amount = fields.Float('Terpakai')
    amount = fields.Float('Nilai Transaksi')
    result_code = fields.Char('Kode Hasil', index=True)
    message = fields.Text('Pesan')


class PkatLockLog(models.Model):
    """DM-13. Riwayat perubahan status kunci kantung."""
    _name = 'pkat.lock.log'
    _description = 'Log Penguncian Kantung'
    _order = 'id desc'

    pocket_id = fields.Many2one('pkat.pocket', 'Kantung', required=True, ondelete='cascade')
    company_id = fields.Many2one(related='pocket_id.company_id', store=True)
    lock_type = fields.Selection([('po', 'PO'), ('real', 'Realisasi'), ('manual', 'Manual')], 'Jenis')
    locked = fields.Boolean('Terkunci')
    reason = fields.Text('Alasan')


class PkatApiLog(models.Model):
    """DM-14. Setiap panggilan API (BRD IN-05). Juga penyimpan respons idempoten."""
    _name = 'pkat.api.log'
    _description = 'Log API PKAT'
    _order = 'id desc'

    company_id = fields.Many2one('res.company', string='Unit/PG', index=True)
    endpoint = fields.Char(index=True)
    idem_key = fields.Char('Kunci Idempotensi', index=True)
    user_login = fields.Char('Pengguna Odoo 10')
    status = fields.Char()
    code = fields.Char()
    duration_ms = fields.Integer('Durasi (ms)')
    remote_addr = fields.Char('Alamat Asal')
    response_json = fields.Text('Respons Tersimpan')


class PkatReconcile(models.Model):
    """DM-15. Hasil rekonsiliasi harian jurnal Odoo 10 vs realisasi Odoo 20 (BRD IN-08)."""
    _name = 'pkat.reconcile'
    _description = 'Rekonsiliasi Realisasi'
    _order = 'id desc'

    company_id = fields.Many2one('res.company', string='Unit/PG', index=True)
    year = fields.Integer('Tahun')
    month = fields.Integer('Bulan')
    account_id = fields.Many2one('pkat.account', 'Perkiraan')
    total_odoo10 = fields.Float('Total Odoo 10')
    total_odoo20 = fields.Float('Total Odoo 20')
    difference = fields.Float('Selisih')
    resolved = fields.Boolean('Sudah Ditindaklanjuti')
