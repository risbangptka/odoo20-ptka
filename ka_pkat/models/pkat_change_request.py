from odoo import _, api, fields, models
from odoo.exceptions import UserError

CR_STATES = [
    ('draft', 'Draft'),
    ('submitted', 'Diajukan'),
    ('approved_unit', 'Disetujui Pemimpin Pabrik'),
    ('waiting_kd', 'Menunggu Bagian Anggaran KD'),
    ('processed', 'Diproses'),
    ('rejected', 'Ditolak'),
]
LINE_KINDS = [('G', 'Pergeseran (G)'), ('T', 'Tambahan (T)'), ('J', 'Geser Jadwal Bulan (J)')]


class PkatChangeRequest(models.Model):
    """DM-11. Permohonan pergeseran / tambahan anggaran (BRD 3.6, 3.7).

    Alur tanpa baris T : draft -> submitted -> processed (disetujui Pemimpin Pabrik)
    Alur dengan baris T: draft -> submitted -> approved_unit -> waiting_kd -> processed
    """
    _name = 'pkat.change.request'
    _description = 'Permohonan Pergeseran / Tambahan Anggaran'
    _inherit = ['mail.thread']
    _order = 'date desc, id desc'

    name = fields.Char('Nomor', default='/', readonly=True, copy=False)
    date = fields.Date('Tanggal', default=fields.Date.context_today, required=True)
    company_id = fields.Many2one('res.company', string='Unit/PG', required=True,
                                 default=lambda self: self.env.company)
    currency_id = fields.Many2one(related='company_id.currency_id')
    year = fields.Integer('Tahun Anggaran', required=True,
                          default=lambda self: fields.Date.today().year)
    requester_id = fields.Many2one('res.users', 'Pengaju (TUK Unit)',
                                   default=lambda self: self.env.user, readonly=True)
    state = fields.Selection(CR_STATES, 'Status', default='draft', required=True, tracking=True)
    line_ids = fields.One2many('pkat.change.request.line', 'request_id', 'Rincian')
    has_addition = fields.Boolean('Ada Tambahan', compute='_compute_has_addition', store=True)
    amount_total = fields.Monetary('Jumlah', compute='_compute_has_addition', store=True)
    letter_number = fields.Char('No. Surat Persetujuan', tracking=True)
    letter_date = fields.Date('Tgl. Surat Persetujuan')
    letter_attachment = fields.Binary('Lampiran Surat')
    reject_reason = fields.Text('Alasan Penolakan')

    @api.depends('line_ids.kind', 'line_ids.amount')
    def _compute_has_addition(self):
        for rec in self:
            rec.has_addition = any(l.kind == 'T' for l in rec.line_ids)
            rec.amount_total = sum(rec.line_ids.mapped('amount'))

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', '/') == '/':
                vals['name'] = self.env['ir.sequence'].next_by_code('pkat.change.request') or '/'
        return super().create(vals_list)

    def action_submit(self):
        for rec in self:
            if not rec.line_ids:
                raise UserError(_("Isi rincian permohonan terlebih dahulu."))
            rec.line_ids._validate()
        self.write({'state': 'submitted'})

    def action_approve_unit(self):
        """Persetujuan Pemimpin Pabrik (SRS FS-SW-06, FS-TA-01, AK-06)."""
        for rec in self:
            if rec.requester_id == self.env.user:
                raise UserError(_("Pengaju tidak dapat menyetujui permohonannya sendiri."))
            rec.line_ids._validate()
            if rec.has_addition:
                rec.state = 'waiting_kd'
            else:
                rec._apply()
                rec.state = 'processed'

    def action_process(self):
        """Persetujuan sistem oleh Bagian Anggaran KD setelah Direksi setuju (FS-TA-02)."""
        for rec in self:
            if rec.state != 'waiting_kd':
                raise UserError(_("Hanya permohonan berstatus menunggu Bagian Anggaran yang dapat diproses."))
            if not rec.letter_number or not rec.letter_date:
                raise UserError(_("Isi nomor dan tanggal surat persetujuan Direksi."))
            rec._apply()
            rec.state = 'processed'

    def action_reject(self):
        for rec in self:
            if not rec.reject_reason:
                raise UserError(_("Isi alasan penolakan."))
        self.write({'state': 'rejected'})

    def _apply(self):
        """Terapkan ke anggaran. TODO(SRS FS-SW-06, FS-SW-07, FS-TA-05):
        shift_in/shift_out/amount_added, penyesuaian rencana bulanan,
        hitung ulang kantung, notifikasi ke Bagian Anggaran KD."""
        raise UserError(_("Penerapan permohonan belum diimplementasikan."))


class PkatChangeRequestLine(models.Model):
    _name = 'pkat.change.request.line'
    _description = 'Rincian Permohonan Pergeseran / Tambahan'

    request_id = fields.Many2one('pkat.change.request', required=True, ondelete='cascade')
    company_id = fields.Many2one(related='request_id.company_id', store=True)
    currency_id = fields.Many2one(related='company_id.currency_id')
    kind = fields.Selection(LINE_KINDS, 'G/T/J', required=True, default='G')
    receiver_line_id = fields.Many2one('pkat.budget.line', 'Akun Penerima')
    receiver_project_id = fields.Many2one('pkat.project', 'Nomor Investasi Penerima')
    giver_line_id = fields.Many2one('pkat.budget.line', 'Akun Pemberi')
    month_from = fields.Integer('Dari Bulan')
    month_to = fields.Integer('Ke Bulan')
    amount = fields.Monetary('Anggaran (Rp)', required=True)
    reason = fields.Text('Alasan', required=True)
    benefit_risk = fields.Text('Manfaat / Risiko')
    sdm_coordinated = fields.Boolean('Sudah koordinasi Divisi SDM & Umum')
    pct_of_budget = fields.Float('% thd PKAT', readonly=True)
    approval_tier = fields.Selection([
        ('direksi', 'Direksi'), ('dekom', 'Dewan Komisaris'), ('pemegang_saham', 'Pemegang Saham'),
    ], 'Jenjang Persetujuan', readonly=True)

    def _validate(self):
        """TODO(SRS FS-SW-02 s.d. FS-SW-05, FS-TA-03). Aturan yang harus dicek:
        - G: amount <= anggaran pemberi - max(realisasi, serapan)
        - G: company sama; stasiun sama / bagian sama / antar bagian satu unit
        - jenis biaya 00/01 hanya ke jenis biaya yang sama; upah -> wajib sdm_coordinated
        - antar bagian: hanya non_upah<->non_upah atau sesama bahan_baku_tebu
        - is_spt tidak boleh jadi pemberi/penerima; tidak ada biaya<->investasi
        - T investasi: hitung pct kumulatif thd PKAT awal -> approval_tier
        """
        for line in self:
            if line.amount <= 0:
                raise UserError(_("Nilai permohonan harus lebih dari nol."))
            if line.kind == 'G' and not line.giver_line_id:
                raise UserError(_("Baris pergeseran wajib mengisi akun pemberi."))
