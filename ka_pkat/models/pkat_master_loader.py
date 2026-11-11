"""Pemuatan master dari ekspor Odoo 10 (PERUBAHAN_DESAIN_01 bagian 3 butir 6; K3, V1-V6, V10).

Masukan: baris-baris dict hasil `tools/export_master_odoo10.sh` (CSV). Tidak ada koneksi ke
Odoo 10 dari sini. Setiap pemuat:
- idempoten (kunci ka10_id; perkiraan juga per Unit/PG),
- memeriksa per baris; baris bermasalah ditolak dengan alasan, tidak ditebak (V5),
- mengembalikan laporan dict: created, updated, rejected [(baris, alasan)], dan daftar khusus.

Sinkronisasi otomatis (API-08) menyusul di Sprint 2 dan akan memakai pemuat yang sama.
"""
import csv
import logging
import os
import re
from collections import Counter, defaultdict

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError

from .account_account import pkat_wage_type

_logger = logging.getLogger(__name__)

# V5: pemetaan tipe perkiraan Odoo 10 (xmlid account.account.type) -> account_type Odoo 20.
ACCOUNT_TYPE_MAP = {
    'account.data_account_type_receivable': 'asset_receivable',
    'account.data_account_type_payable': 'liability_payable',
    'account.data_account_type_liquidity': 'asset_cash',
    'account.data_account_type_credit_card': 'liability_credit_card',
    'account.data_account_type_current_assets': 'asset_current',
    'account.data_account_type_non_current_assets': 'asset_non_current',
    'account.data_account_type_prepayments': 'asset_prepayments',
    'account.data_account_type_fixed_assets': 'asset_fixed',
    'account.data_account_type_current_liabilities': 'liability_current',
    'account.data_account_type_non_current_liabilities': 'liability_non_current',
    'account.data_account_type_equity': 'equity',
    'account.data_unaffected_earnings': 'equity_unaffected',
    'account.data_account_type_revenue': 'income',
    'account.data_account_type_other_income': 'income_other',
    'account.data_account_type_expenses': 'expense',
    'account.data_account_type_depreciation': 'expense_depreciation',
    'account.data_account_type_direct_costs': 'expense_direct_cost',
}
# V3/P4: tipe yang menjadi perkiraan induk / tidak boleh dianggarkan.
VIEW_TYPES = {'ka_account.data_account_type_view', 'ka_account.data_account_type_unpostable'}
# V3: tipe yang tidak boleh diberikan ke perkiraan induk.
NO_VIEW_ACCOUNT_TYPES = {'asset_cash', 'liability_credit_card'}
VIEW_FALLBACK_TYPE = 'off_balance'
# Kelompok PKAT hanya ditentukan untuk perkiraan laba-rugi; neraca dibiarkan kosong.
KIND_BY_ACCOUNT_TYPE = {
    'income': 'income', 'income_other': 'income',
    'expense': 'expense', 'expense_depreciation': 'expense', 'expense_direct_cost': 'expense',
}
ODOO20_CODE_RE = re.compile(r'^[A-Za-z0-9.-]+$')  # sama dengan ACCOUNT_CODE_REGEX core
TRUE_VALUES = {'t', 'true', '1', 'True', True}


def _int(value):
    return int(value) if value not in (None, '', False) else 0


def _bool(value):
    return value in TRUE_VALUES


class PkatUomMap(models.Model):
    """V6: tabel padanan satuan Odoo 10 -> uom.uom Odoo 20. Diisi setelah disetujui pemilik;
    satuan tanpa padanan tidak dibuat otomatis dan barangnya tidak dimuat."""
    _name = 'pkat.uom.map'
    _description = 'Padanan Satuan Odoo 10'
    _order = 'name'

    ka10_id = fields.Integer('ID Satuan Odoo 10', required=True, index=True)
    name = fields.Char('Satuan Odoo 10', required=True)
    category = fields.Char('Kategori Odoo 10')
    uom_id = fields.Many2one('uom.uom', 'Satuan Odoo 20')
    note = fields.Char('Catatan')

    _ka10_uniq = models.Constraint('unique(ka10_id)', 'Satuan Odoo 10 ini sudah ada di tabel padanan.')


class PkatMasterLoader(models.AbstractModel):
    _name = 'pkat.master.loader'
    _description = 'Pemuat Master dari Ekspor Odoo 10'

    # ------------------------------------------------------------ umum
    @api.model
    def _report(self):
        return {'created': 0, 'updated': 0, 'rejected': [], 'notes': []}

    @api.model
    def _companies_by_code(self):
        """Padanan Unit/PG lewat res.company.code (ka_base); sama di Odoo 10 dan Odoo 20."""
        return {company.code: company for company in self.env['res.company'].sudo().search([])
                if company.code}

    @api.model
    def _upsert(self, record, model, vals, report):
        """Tulis/buat satu record dalam savepoint; galat validasi -> baris ditolak."""
        created = not record
        try:
            with self.env.cr.savepoint():
                if record:
                    record.write(vals)
                else:
                    record = model.create(vals)
                record.flush_recordset()
        except (UserError, ValidationError) as exc:
            return exc
        report['created' if created else 'updated'] += 1
        return record

    # ------------------------------------------------------- departemen
    @api.model
    def load_departments(self, rows):
        """K7/V9. Kolom: id, name, code, parent_id, company_code, active, bagian_kode."""
        report = self._report()
        companies = self._companies_by_code()
        Dept = self.env['hr.department'].with_context(active_test=False)
        existing = {d.ka10_id: d for d in Dept.search([('ka10_id', '>', 0)])}
        loaded = {}
        for row in rows:
            company = companies.get(row['company_code'])
            if not company:
                report['rejected'].append((row, _("Unit/PG berkode %s tidak ada di Odoo 20.",
                                                  row['company_code'])))
                continue
            vals = {'name': row['name'], 'company_id': company.id, 'active': _bool(row['active']),
                    'pkat_code': row.get('bagian_kode') or False, 'ka10_id': _int(row['id'])}
            result = self._upsert(existing.get(vals['ka10_id']), Dept, vals, report)
            if isinstance(result, Exception):
                report['rejected'].append((row, str(result)))
            else:
                loaded[vals['ka10_id']] = result
        # induk dipasang setelah semua departemen ada
        for row in rows:
            dept, parent_id = loaded.get(_int(row['id'])), _int(row['parent_id'])
            if not dept or not parent_id:
                continue
            parent = loaded.get(parent_id)
            if not parent:
                report['notes'].append((row, _("Induk (id %s) tidak dimuat; induk dikosongkan.", parent_id)))
                continue
            if dept.parent_id != parent:
                result = self._upsert(dept, Dept, {'parent_id': parent.id}, self._report())
                if isinstance(result, Exception):
                    report['notes'].append((row, _("Induk tidak dapat dipasang: %s", result)))
        return report

    # ---------------------------------------------------------- stasiun
    @api.model
    def load_cost_centers(self, rows):
        """Kolom: id, kode, name, company_code, bagian_kode, department_id, seksi_id,
        sub_seksi_id, active (id departemen = id hr.department Odoo 10)."""
        report = self._report()
        companies = self._companies_by_code()
        depts = {d.ka10_id: d for d in self.env['hr.department'].with_context(active_test=False).search(
            [('ka10_id', '>', 0)])}
        Center = self.env['pkat.cost.center'].with_context(active_test=False)
        existing = {c.ka10_id: c for c in Center.search([('ka10_id', '>', 0)])}
        seen = {}
        for row in rows:
            company = companies.get(row['company_code'])
            code = (row['kode'] or '').strip()
            department = depts.get(_int(row['department_id']))
            reason = None
            if not company:
                reason = _("Unit/PG berkode %s tidak ada di Odoo 20.", row['company_code'])
            elif not code:
                reason = _("Kode stasiun kosong.")
            elif (company.id, code) in seen:
                reason = _("Kode stasiun %(code)s dobel dengan id %(other)s pada Unit/PG yang sama.",
                           code=code, other=seen[company.id, code])
            elif not department:
                reason = _("Bagian stasiun (departemen id %s) tidak dimuat.", row['department_id'] or '-')
            if reason:
                report['rejected'].append((row, reason))
                continue
            seen[company.id, code] = row['id']
            vals = {
                'code': code, 'name': row['name'], 'company_id': company.id,
                'department_id': department.id,
                'section_id': depts.get(_int(row['seksi_id']), Center.env['hr.department']).id,
                'subsection_id': depts.get(_int(row['sub_seksi_id']), Center.env['hr.department']).id,
                'active': _bool(row['active']), 'ka10_id': _int(row['id']),
            }
            result = self._upsert(existing.get(vals['ka10_id']), Center, vals, report)
            if isinstance(result, Exception):
                report['rejected'].append((row, str(result)))
        return report

    # -------------------------------------------------------- perkiraan
    @api.model
    def _account_types(self, rows):
        """V3/V5: account_type tiap baris. Perkiraan induk mengambil tipe terbanyak dari
        turunan detailnya (tidak pernah kas/bank atau kartu kredit)."""
        types, children = {}, defaultdict(list)
        for row in rows:
            if _int(row['parent_id']):
                children[_int(row['parent_id'])].append(_int(row['id']))
            if row['type_xmlid'] not in VIEW_TYPES:
                types[_int(row['id'])] = ACCOUNT_TYPE_MAP.get(row['type_xmlid'])

        def descendant_types(account_id, trail=()):
            found = Counter()
            for child in children.get(account_id, ()):
                if child in trail:
                    continue
                if child in types:
                    if types[child] and types[child] not in NO_VIEW_ACCOUNT_TYPES:
                        found[types[child]] += 1
                else:
                    found.update(descendant_types(child, trail + (account_id,)))
            return found

        fallback = []
        for row in rows:
            account_id = _int(row['id'])
            if row['type_xmlid'] in VIEW_TYPES:
                counted = descendant_types(account_id)
                if counted:
                    types[account_id] = sorted(counted.items(), key=lambda kv: (-kv[1], kv[0]))[0][0]
                else:
                    types[account_id] = VIEW_FALLBACK_TYPE
                    fallback.append(row)
        return types, fallback

    @api.model
    def load_accounts(self, rows):
        """K1/K3/K8. Kolom: id, code, name, company_code, parent_id, type_xmlid, type_name,
        stasiun_id, bagian_id, upah, is_detail, deprecated."""
        report = self._report()
        report.update(wage_diff=[], view_fallback=[])
        companies = self._companies_by_code()
        centers = {c.ka10_id: c for c in self.env['pkat.cost.center'].with_context(
            active_test=False).search([('ka10_id', '>', 0)])}
        depts = {d.ka10_id: d for d in self.env['hr.department'].with_context(
            active_test=False).search([('ka10_id', '>', 0)])}
        Account = self.env['account.account'].with_context(active_test=False)
        existing = {(a.pkat_company_id.id, a.ka10_id): a for a in Account.search(
            [('pkat_managed', '=', True), ('ka10_id', '>', 0)])}
        types, report['view_fallback'] = self._account_types(rows)
        seen, loaded = {}, {}
        for row in rows:
            company = companies.get(row['company_code'])
            code = (row['code'] or '').strip()
            account_id = _int(row['id'])
            is_view = row['type_xmlid'] in VIEW_TYPES
            reason = None
            if not company:
                reason = _("Unit/PG berkode %s tidak ada di Odoo 20.", row['company_code'])
            elif not ODOO20_CODE_RE.match(code):
                reason = _("Kode '%s' tidak diterima Odoo 20 (hanya huruf, angka, titik, tanda hubung).",
                           code)
            elif (company.id, code) in seen:
                reason = _("Kode %(code)s dobel dengan id %(other)s pada Unit/PG yang sama.",
                           code=code, other=seen[company.id, code])
            elif not types.get(account_id):
                reason = _("Tipe perkiraan '%(name)s' (%(xmlid)s) tidak ada di tabel pemetaan.",
                           name=row.get('type_name'), xmlid=row['type_xmlid'] or '-')
            if reason:
                report['rejected'].append((row, reason))
                continue
            seen[company.id, code] = row['id']
            account_type = types[account_id]
            vals = {
                'name': row['name'], 'code': code, 'account_type': account_type,
                'active': not _bool(row['deprecated']),
                'pkat_managed': True, 'pkat_is_view': is_view, 'ka10_id': account_id,
                'pkat_kind': False if is_view else KIND_BY_ACCOUNT_TYPE.get(account_type, False),
            }
            if not is_view:
                # nilai eksplisit Odoo 10 didahulukan; bila kosong diturunkan dari kode (V2)
                center = centers.get(_int(row['stasiun_id']))
                dept = depts.get(_int(row['bagian_id']))
                if center and center.company_id == company:
                    vals['pkat_cost_center_id'] = center.id
                if dept and dept.company_id == company:
                    vals['pkat_department_id'] = dept.id
            record = existing.get((company.id, account_id))
            ScopedAccount = Account.with_company(company).with_context(
                skip_auto_account_journal_creation=True)  # V4
            if record:
                result = self._upsert(record.with_company(company), ScopedAccount, vals, report)
            else:
                result = self._upsert(None, ScopedAccount, dict(vals, company_ids=[(6, 0, company.ids)]),
                                      report)
            if isinstance(result, Exception):
                report['rejected'].append((row, str(result)))
                continue
            loaded[account_id] = result
            if not is_view:
                result._pkat_fill_owner()
                # V10: daftar perkiraan yang jenis upahnya berbeda dari Odoo 10
                wage20 = pkat_wage_type(code)
                if (row.get('upah') or 'non_upah') != wage20:
                    report['wage_diff'].append({
                        'code': code, 'name': row['name'], 'company_code': row['company_code'],
                        'odoo10': row.get('upah') or '', 'odoo20': wage20})
        # induk-anak (K8) dipasang setelah semua perkiraan ada
        for row in rows:
            account, parent_id = loaded.get(_int(row['id'])), _int(row['parent_id'])
            if not account or not parent_id:
                continue
            parent = loaded.get(parent_id)
            if not parent:
                report['notes'].append((row, _("Induk (id %s) tidak dimuat; induk dikosongkan.", parent_id)))
            elif account.parent_id != parent:
                result = self._upsert(account, Account, {'parent_id': parent.id}, self._report())
                if isinstance(result, Exception):
                    report['notes'].append((row, _("Induk tidak dapat dipasang: %s", result)))
        return report

    # ----------------------------------------------------------- satuan
    @api.model
    def uom_report(self, uom_rows):
        """V6: satuan Odoo 10 yang dipakai barang, padanannya (bila sudah disetujui), dan
        usulan padanan berdasarkan nama. Tidak membuat atau mengubah apa pun."""
        mapping = {m.ka10_id: m for m in self.env['pkat.uom.map'].search([])}
        by_name = defaultdict(list)
        for uom in self.env['uom.uom'].with_context(active_test=False, lang='en_US').search([]):
            by_name[(uom.name or '').strip().lower()].append(uom)
        result = []
        for row in uom_rows:
            if not _int(row.get('product_count')):
                continue
            mapped = mapping.get(_int(row['id']))
            candidates = by_name.get((row['name'] or '').strip().lower(), [])
            result.append({
                'ka10_id': _int(row['id']), 'name': row['name'], 'category': row.get('category'),
                'product_count': _int(row['product_count']),
                'mapped': mapped.uom_id.display_name if mapped and mapped.uom_id else '',
                'suggestion': candidates[0].display_name if len(candidates) == 1 else '',
            })
        return result

    # ----------------------------------------------------------- barang
    @api.model
    def load_products(self, rows):
        """K2/V6. Kolom: tmpl_id, product_id, default_code, name, uom_id, uom_name, active.
        Barang yang satuannya belum punya padanan disetujui tidak dimuat."""
        report = self._report()
        mapping = {m.ka10_id: m.uom_id for m in self.env['pkat.uom.map'].search([]) if m.uom_id}
        Template = self.env['product.template'].with_context(active_test=False)
        existing = {t.ka10_id: t for t in Template.search(
            [('pkat_managed', '=', True), ('ka10_id', '>', 0)])}
        seen, to_create = {}, []
        for row in rows:
            code = (row['default_code'] or '').strip()
            uom = mapping.get(_int(row['uom_id']))
            reason = None
            if not code:
                reason = _("Kode barang kosong.")
            elif code in seen:
                reason = _("Kode barang %(code)s dobel dengan id %(other)s.", code=code, other=seen[code])
            elif not uom:
                reason = _("Satuan '%s' belum punya padanan yang disetujui (V6).", row.get('uom_name'))
            if reason:
                report['rejected'].append((row, reason))
                continue
            seen[code] = row['tmpl_id']
            vals = {'default_code': code, 'name': row['name'], 'uom_id': uom.id,
                    'active': _bool(row['active']), 'ka10_id': _int(row['tmpl_id'])}
            record = existing.get(vals['ka10_id'])
            if record:
                changed = {k: v for k, v in vals.items() if (
                    record[k].id if k == 'uom_id' else record[k]) != v}
                if changed:
                    record.write(changed)
                    report['updated'] += 1
            else:
                to_create.append(vals)
        for start in range(0, len(to_create), 1000):
            Template._pkat_create(to_create[start:start + 1000])
            self.env.flush_all()
            self.env.invalidate_all()
        report['created'] = len(to_create)
        return report

    # ------------------------------------------------------ dari berkas
    @api.model
    def _read_csv(self, path):
        with open(path, newline='', encoding='utf-8') as handle:
            return list(csv.DictReader(handle))

    @api.model
    def _write_csv(self, path, headers, rows):
        with open(path, 'w', newline='', encoding='utf-8') as handle:
            writer = csv.writer(handle)
            writer.writerow(headers)
            writer.writerows(rows)

    @api.model
    def load_directory(self, path, products=False):
        """Muat master dari folder hasil ekspor; laporan ditulis ke <path>/laporan.
        Barang hanya dimuat bila products=True (setelah tabel padanan satuan disetujui)."""
        out = os.path.join(path, 'laporan')
        os.makedirs(out, exist_ok=True)
        summary = {}
        steps = [('department', self.load_departments), ('cost_center', self.load_cost_centers),
                 ('account', self.load_accounts)]
        if products:
            steps.append(('product', self.load_products))
        for name, loader in steps:
            rows = self._read_csv(os.path.join(path, name + '.csv'))
            report = loader(rows)
            headers = list(rows[0].keys()) if rows else []
            self._write_csv(os.path.join(out, name + '_ditolak.csv'), headers + ['alasan'], [
                [row.get(h) for h in headers] + [reason] for row, reason in report['rejected']])
            if report['notes']:
                self._write_csv(os.path.join(out, name + '_catatan.csv'), headers + ['catatan'], [
                    [row.get(h) for h in headers] + [note] for row, note in report['notes']])
            if name == 'account':
                self._write_csv(
                    os.path.join(out, 'selisih_upah_v10.csv'),
                    ['perkiraan', 'nama', 'kode_unit', 'odoo10', 'odoo20'],
                    [[d['code'], d['name'], d['company_code'], d['odoo10'], d['odoo20']]
                     for d in report['wage_diff']])
                self._write_csv(
                    os.path.join(out, 'induk_tanpa_tipe_anak.csv'), headers,
                    [[row.get(h) for h in headers] for row in report['view_fallback']])
            summary[name] = {'baris': len(rows), 'dibuat': report['created'],
                             'diperbarui': report['updated'], 'ditolak': len(report['rejected']),
                             'catatan': len(report['notes'])}
            _logger.info("Master %s: %s", name, summary[name])
        uoms = self.uom_report(self._read_csv(os.path.join(path, 'uom.csv')))
        self._write_csv(
            os.path.join(out, 'satuan_padanan.csv'),
            ['id_odoo10', 'satuan_odoo10', 'kategori_odoo10', 'jumlah_barang', 'padanan_disetujui',
             'usulan_dari_nama'],
            [[u['ka10_id'], u['name'], u['category'], u['product_count'], u['mapped'], u['suggestion']]
             for u in uoms])
        summary['satuan_tanpa_padanan'] = len([u for u in uoms if not u['mapped']])
        return summary
