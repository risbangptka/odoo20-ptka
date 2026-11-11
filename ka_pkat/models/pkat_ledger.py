from odoo import fields, models


class PkatCommitment(models.Model):
    """DM-08. Buku serapan: satu baris per baris PO Odoo 10 (BRD SR-02, BR-02).
    Hanya ditulis lewat services/API (commitment/check, commitment/cancel)."""
    _name = 'pkat.commitment'
    _description = 'Buku Serapan (PO)'
    _order = 'po_date desc, id desc'

    idem_key = fields.Char('Kunci Idempotensi', required=True, index=True, copy=False)
    company_id = fields.Many2one('res.company', string='Unit/PG', required=True, index=True)
    currency_id = fields.Many2one(related='company_id.currency_id')
    po_number = fields.Char('No. PO', required=True, index=True)
    po_line_ref = fields.Char('Ref. Baris PO')
    po_date = fields.Date('Tanggal PO', required=True, index=True)
    partner_name = fields.Char('Rekanan')
    po_kind = fields.Selection([('rutin', 'Rutin'), ('plb', 'PLB'), ('investasi', 'Investasi')],
                               'Jenis PO', default='rutin', required=True)
    account_id = fields.Many2one('account.account', 'Perkiraan', index=True)
    budget_line_id = fields.Many2one('pkat.budget.line', 'Anggaran Perkiraan', index=True)
    project_id = fields.Many2one('pkat.project', 'Nomor Investasi', index=True)
    amount = fields.Monetary('Nilai (tanpa PPN)', required=True)
    state = fields.Selection([('active', 'Aktif'), ('cancelled', 'Dibatalkan')],
                             default='active', required=True, index=True)
    mirror_of_id = fields.Many2one('pkat.commitment', 'Cermin dari (PO PLB)', ondelete='cascade')
    is_migration = fields.Boolean('Serapan Awal (Migrasi)')

    _idem_key_uniq = models.Constraint('unique(idem_key)', 'Kunci idempotensi sudah dipakai.')


class PkatRealization(models.Model):
    """DM-09. Buku realisasi: satu baris per baris jurnal posted Odoo 10 (BRD SR-04)."""
    _name = 'pkat.realization'
    _description = 'Buku Realisasi (Jurnal)'
    _order = 'date desc, id desc'

    company_id = fields.Many2one('res.company', string='Unit/PG', required=True, index=True)
    currency_id = fields.Many2one(related='company_id.currency_id')
    src_move_line_id = fields.Integer('ID Baris Jurnal Odoo 10', required=True, index=True)
    move_name = fields.Char('No. Jurnal')
    date = fields.Date('Tanggal', required=True, index=True)
    source_type = fields.Selection([
        ('bon', 'Bon Barang/Jasa'), ('ba_ntb', 'Berita Acara / NTB'),
        ('kas_bank', 'Kas/Bank'), ('memo', 'Memo/Koreksi'), ('lainnya', 'Lainnya'),
    ], 'Sumber', default='lainnya')
    source_number = fields.Char('No. Dokumen Sumber')
    account_id = fields.Many2one('account.account', 'Perkiraan', index=True)
    budget_line_id = fields.Many2one('pkat.budget.line', 'Anggaran Perkiraan', index=True)
    project_id = fields.Many2one('pkat.project', 'Nomor Investasi', index=True)
    debit = fields.Monetary('Debet')
    credit = fields.Monetary('Kredit')
    is_correction = fields.Boolean('Kor.', help="Tanda koreksi PKAT dari jurnal Odoo 10.")
    # Biaya: debit - kredit. Proyek: debit; kredit hanya bila is_correction (BRD IV-02).
    amount_counted = fields.Monetary('Nilai Dihitung')
    state = fields.Selection([('posted', 'Posted'), ('reversed', 'Dibalik')],
                             default='posted', required=True, index=True)

    _src_line_uniq = models.Constraint(
        'unique(company_id, src_move_line_id)', 'Baris jurnal ini sudah tercatat.')


class PkatPotential(models.Model):
    """DM-10. Potensi serapan: baris SPM/SPPJ yang masih diproses."""
    _name = 'pkat.potential'
    _description = 'Potensi Serapan (SPM/SPPJ)'
    _order = 'date desc, id desc'

    idem_key = fields.Char('Kunci Idempotensi', required=True, index=True, copy=False)
    company_id = fields.Many2one('res.company', string='Unit/PG', required=True, index=True)
    currency_id = fields.Many2one(related='company_id.currency_id')
    doc_type = fields.Selection([('spm', 'SPM'), ('sppj', 'SPPJ')], 'Jenis', required=True)
    doc_number = fields.Char('No. Dokumen', required=True)
    date = fields.Date('Tanggal', required=True)
    account_id = fields.Many2one('account.account', 'Perkiraan')
    budget_line_id = fields.Many2one('pkat.budget.line', 'Anggaran Perkiraan')
    project_id = fields.Many2one('pkat.project', 'Nomor Investasi')
    amount = fields.Monetary('HPS x Kuantum')
    state = fields.Selection([('open', 'Diproses'), ('converted', 'Sudah PO'), ('cancelled', 'Batal')],
                             default='open', required=True)
    over_budget = fields.Boolean('Melebihi Anggaran')
    reason = fields.Text('Alasan Permintaan')

    _idem_key_uniq = models.Constraint('unique(idem_key)', 'Kunci idempotensi sudah dipakai.')
