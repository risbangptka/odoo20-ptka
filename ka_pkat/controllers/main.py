"""API Anggaran (SRS bab 5). Alamat dasar: /api/pkat/v1/

Header wajib (SRS API-G-02):
    X-PKAT-Token, X-PKAT-Company, X-PKAT-User, X-Idempotency-Key (layanan yang mengubah data)

Amplop respons (SRS API-G-06): {"status", "code", "message", "data"}
HTTP 200 untuk ok/warn/reject; 4xx/5xx hanya untuk galat teknis.

STATUS: baru `ping` yang berfungsi. Layanan lain masih kerangka (ERR_NOT_IMPLEMENTED).
Catatan Odoo 20: argumen route (type='http', auth='public', csrf=False) sudah dicek
terhadap core (odoo/http/routing_map.py) dan teruji lewat `ping`.
"""
import json
import logging
import time

from odoo import fields, http
from odoo.http import request

_logger = logging.getLogger(__name__)

BASE = '/api/pkat/v1'


def _envelope(status, code, message='', data=None, http_status=200):
    body = {'status': status, 'code': code, 'message': message, 'data': data or {}}
    return request.make_json_response(body, status=http_status)


class PkatApi(http.Controller):

    # ------------------------------------------------------------------ util
    def _auth(self):
        """Kembalikan (token_record, payload) atau (None, respons_galat)."""
        headers = request.httprequest.headers
        token = request.env['pkat.api.token']._authenticate(
            headers.get('X-PKAT-Company'), headers.get('X-PKAT-Token'))
        if not token:
            return None, _envelope('error', 'ERR_AUTH', 'Tidak berwenang.', http_status=401)
        try:
            payload = json.loads(request.httprequest.get_data(as_text=True) or '{}')
        except ValueError:
            return None, _envelope('error', 'ERR_VALIDATION', 'Isi permintaan bukan JSON yang sah.',
                                   http_status=400)
        return token, payload

    def _log(self, token, endpoint, started, status, code, response=None):
        headers = request.httprequest.headers
        request.env['pkat.api.log'].sudo().create({
            'company_id': token.company_id.id if token else False,
            'endpoint': endpoint,
            'idem_key': headers.get('X-Idempotency-Key'),
            'user_login': headers.get('X-PKAT-User'),
            'status': status,
            'code': code,
            'duration_ms': int((time.time() - started) * 1000),
            'remote_addr': request.httprequest.remote_addr,
            'response_json': json.dumps(response) if response else False,
        })

    def _not_implemented(self, endpoint):
        started = time.time()
        token, payload = self._auth()
        if not token:
            return payload
        self._log(token, endpoint, started, 'error', 'ERR_NOT_IMPLEMENTED')
        return _envelope('error', 'ERR_NOT_IMPLEMENTED',
                         'Layanan %s belum diimplementasikan.' % endpoint, http_status=501)

    # ------------------------------------------------------------- layanan
    @http.route(BASE + '/ping', type='http', auth='public', methods=['POST'], csrf=False)
    def ping(self, **kw):
        """API-11."""
        started = time.time()
        token, payload = self._auth()
        if not token:
            return payload
        data = {'server_time': fields.Datetime.to_string(fields.Datetime.now()),
                'company': token.company_id.code}
        self._log(token, 'ping', started, 'ok', 'OK')
        return _envelope('ok', 'OK', 'Layanan anggaran aktif.', data)

    @http.route(BASE + '/budget/list', type='http', auth='public', methods=['POST'], csrf=False)
    def budget_list(self, **kw):
        """API-01. Daftar anggaran berstatus Disetujui, disaring hak akses pengguna."""
        return self._not_implemented('budget/list')

    @http.route(BASE + '/budget/info', type='http', auth='public', methods=['POST'], csrf=False)
    def budget_info(self, **kw):
        """API-02. Posisi anggaran perkiraan / Nomor Investasi."""
        return self._not_implemented('budget/info')

    @http.route(BASE + '/spm/check', type='http', auth='public', methods=['POST'], csrf=False)
    def spm_check(self, **kw):
        """API-03. Cek SPM/SPPJ (peringatan) + catat potensi bila simpan=ya."""
        return self._not_implemented('spm/check')

    @http.route(BASE + '/commitment/check', type='http', auth='public', methods=['POST'], csrf=False)
    def commitment_check(self, **kw):
        """API-04. Cek serapan PO + catat buku serapan secara atomik.
        Langkah: idempotensi -> petakan baris -> kunci pocket/project (FOR UPDATE)
        -> services.engine.check_document(KIND_PO, ...) -> tulis pkat.commitment + agregat + log."""
        return self._not_implemented('commitment/check')

    @http.route(BASE + '/commitment/cancel', type='http', auth='public', methods=['POST'], csrf=False)
    def commitment_cancel(self, **kw):
        """API-05. PO batal: lepas serapan."""
        return self._not_implemented('commitment/cancel')

    @http.route(BASE + '/realization/check', type='http', auth='public', methods=['POST'], csrf=False)
    def realization_check(self, **kw):
        """API-06. Cek realisasi (bon, BA/NTB, kas/bank, memo). Tidak mencatat selain log."""
        return self._not_implemented('realization/check')

    @http.route(BASE + '/journal/push', type='http', auth='public', methods=['POST'], csrf=False)
    def journal_push(self, **kw):
        """API-07. Terima baris jurnal posted/unpost/delete (maks 500 baris)."""
        return self._not_implemented('journal/push')

    @http.route(BASE + '/master/sync', type='http', auth='public', methods=['POST'], csrf=False)
    def master_sync(self, **kw):
        """API-08. Sinkron master perkiraan, stasiun, bagian dari Odoo 10."""
        return self._not_implemented('master/sync')

    @http.route(BASE + '/access/scope', type='http', auth='public', methods=['POST'], csrf=False)
    def access_scope(self, **kw):
        """API-09. Unit/bagian/stasiun yang boleh dilihat pengguna (X-PKAT-User)."""
        return self._not_implemented('access/scope')

    @http.route(BASE + '/journal/reconcile', type='http', auth='public', methods=['POST'], csrf=False)
    def journal_reconcile(self, **kw):
        """API-10. Bandingkan total jurnal Odoo 10 vs buku realisasi."""
        return self._not_implemented('journal/reconcile')
