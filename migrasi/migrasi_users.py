"""Migrasi akun login (res.users) Odoo 10 -> Odoo 20.

Dijalankan lewat odoo shell di kontainer web_odoo20 (bukan modul):

    docker exec -e DRY_RUN=1 web_odoo20 sh -c \
      "odoo shell -c /etc/odoo/odoo.conf -d pg_kba --no-http < /mnt/extra-addons/migrasi/migrasi_users.py"

Env:
    SRC_DB        database Odoo 10           (default kebonagung_20261014)
    SRC_HOST      host db_odoo10             (default host.docker.internal)
    SRC_PORT/SRC_USER/SRC_PASSWORD           (default 5432/odoo/odoo)
    DRY_RUN=1     jalankan semua lalu ROLLBACK (tidak menyimpan apa pun)
    MINIMAL=1     hanya login, nama, password, status aktif & tipe user (untuk trial login).
                  Jalankan ulang tanpa MINIMAL untuk melengkapi user yang sama.

Aturan:
* Database Odoo 10 hanya DIBACA (transaksi read-only).
* Hash password (pbkdf2-sha512) disalin apa adanya: user login dengan password lama,
  Odoo 20 memperbarui hash-nya otomatis saat login pertama. Hash tidak pernah dicetak.
* 6 user sistem ka_base TIDAK diberi password lama (KB-01: password-nya bocor di git).
* Template Odoo 10 (default, public, portaltemplate) dilewati.
* Tipe user: internal / portal / public. User share tanpa grup portal -> portal.
* Grup yang dipetakan baru grup base; grup modul lain diberikan saat modulnya di-port.
* Company dipetakan lewat res.company.code (0/1/2/4).
* Pemetaan id lama -> baru disimpan sebagai xmlid __odoo10__.res_users_<id> dan
  __odoo10__.res_partner_<id>, untuk migrasi data modul berikutnya (create_uid, dll.).
* Aman dijalankan ulang: user yang sudah ada (xmlid/login) di-update, grup hanya
  DITAMBAH (grup modul yang diberikan belakangan tidak terhapus).
"""
import os

import psycopg2

from odoo import Command

SRC = {
    'dbname': os.environ.get('SRC_DB', 'kebonagung_20261014'),
    'host': os.environ.get('SRC_HOST', 'host.docker.internal'),
    'port': int(os.environ.get('SRC_PORT', '5432')),
    'user': os.environ.get('SRC_USER', 'odoo'),
    'password': os.environ.get('SRC_PASSWORD', 'odoo'),
}
DRY_RUN = os.environ.get('DRY_RUN', '0') == '1'
MINIMAL = os.environ.get('MINIMAL', '0') == '1'
XMLID_MODULE = '__odoo10__'
SKIP_LOGINS = {'default', 'public', 'portaltemplate'}
NO_PASSWORD_LOGINS = {
    '1540dir', '1540kba', '1540tk',
    'automated_system_direksi', 'automated_system_kba', 'automated_system_trangkil',
}
EXTRA_BASE_GROUPS = ['group_system', 'group_erp_manager', 'group_multi_company',
                     'group_partner_manager', 'group_no_one']
PROTECTED_XMLIDS = ['base.user_root', 'base.user_admin', 'base.public_user', 'base.template_portal_user_id']

SOURCE_SQL = """
    SELECT u.id, u.login, u.active, u.password_crypt, u.signature,
           p.id, p.name, p.email, p.phone, p.mobile, p.tz,
           (SELECT c.code FROM res_company c WHERE c.id = u.company_id),
           ARRAY(SELECT c.code FROM res_company_users_rel r
                   JOIN res_company c ON c.id = r.cid WHERE r.user_id = u.id),
           ARRAY(SELECT d.name FROM res_groups_users_rel r
                   JOIN ir_model_data d ON d.model = 'res.groups' AND d.res_id = r.gid
                  WHERE r.uid = u.id AND d.module = 'base')
      FROM res_users u
      JOIN res_partner p ON p.id = u.partner_id
  ORDER BY u.id
"""


def _phone(phone, mobile):
    # Odoo 20 tidak punya res.partner.mobile lagi: gabung ke phone.
    phone, mobile = (phone or '').strip(), (mobile or '').strip()
    if phone and mobile and phone != mobile:
        return '%s / %s' % (phone, mobile)
    return phone or mobile or False


def migrate_users(env):
    Users = env['res.users'].with_context(
        active_test=False, no_reset_password=True, tracking_disable=True, mail_create_nolog=True)
    IMD = env['ir.model.data']
    group = lambda name: env.ref('base.%s' % name)
    companies = {c.code: c for c in env['res.company'].search([]) if c.code}
    main_company = env.ref('base.main_company')
    protected = Users.browse([env.ref(x).id for x in PROTECTED_XMLIDS if env.ref(x, raise_if_not_found=False)])

    src = psycopg2.connect(**SRC)
    src.set_session(readonly=True)
    with src, src.cursor() as cur:
        cur.execute(SOURCE_SQL)
        rows = cur.fetchall()
    src.close()

    stat = dict(dibaca=len(rows), dibuat=0, diupdate=0, dilewati=0, password=0, gagal=0)
    warnings = []
    for (uid, login, active, pwd_hash, signature, pid, name, email, phone, mobile, tz,
         company_code, company_codes, base_groups) in rows:
        login = (login or '').strip()
        if not login or login.lower() in SKIP_LOGINS:
            stat['dilewati'] += 1
            continue

        if 'group_user' in base_groups and MINIMAL:
            groups = group('group_user')
        elif 'group_user' in base_groups:
            groups = group('group_user') + sum((group(g) for g in EXTRA_BASE_GROUPS if g in base_groups), env['res.groups'])
        elif 'group_public' in base_groups:
            groups = group('group_public')
        else:
            groups = group('group_portal')

        allowed = env['res.company'].browse([companies[c].id for c in company_codes if c in companies])
        default = companies.get(company_code) or (allowed[:1]) or main_company
        allowed |= default
        if not MINIMAL and (company_code not in companies or any(c not in companies for c in company_codes)):
            warnings.append('%s: kode company %s/%s tidak semua ada di Odoo 20' % (login, company_code, company_codes))

        vals = {
            'name': name or login,
            'login': login,
            'email': email or False,
            'phone': _phone(phone, mobile),
            'tz': tz or 'Asia/Jakarta',
            'lang': 'en_US',
            'signature': signature or False,
            'company_id': default.id,
            'company_ids': [Command.set(allowed.ids)],
            'active': active,
        }
        if MINIMAL:
            vals = {k: vals[k] for k in ('name', 'login', 'active')}

        user = env.ref('%s.res_users_%s' % (XMLID_MODULE, uid), raise_if_not_found=False)
        if not user:
            user = Users.search([('login', '=ilike', login)], limit=1)
        if user and user in protected:
            warnings.append('%s: bentrok dengan user bawaan Odoo 20 (%s), dilewati' % (login, user.login))
            stat['dilewati'] += 1
            continue
        system_user = login.lower() in NO_PASSWORD_LOGINS

        try:
            with env.cr.savepoint():
                if user:
                    if not system_user:  # user sistem dikelola ka_base
                        user.write(dict(vals, group_ids=[Command.link(g.id) for g in groups]))
                    stat['diupdate'] += 1
                else:
                    user = Users.create(dict(vals, group_ids=[Command.set(groups.ids)]))
                    stat['dibuat'] += 1
                if pwd_hash and not system_user:
                    env.cr.execute("UPDATE res_users SET password = %s WHERE id = %s", (pwd_hash, user.id))
                    stat['password'] += 1
                IMD._update_xmlids([
                    {'xml_id': '%s.res_users_%s' % (XMLID_MODULE, uid), 'record': user, 'noupdate': True},
                    {'xml_id': '%s.res_partner_%s' % (XMLID_MODULE, pid), 'record': user.partner_id, 'noupdate': True},
                ])
        except Exception as e:  # noqa: BLE001 - lanjutkan user lain, laporkan di akhir
            stat['gagal'] += 1
            warnings.append('%s: GAGAL %s' % (login, e))

    env.invalidate_all()
    return stat, warnings


stat, warnings = migrate_users(env)
for w in warnings:
    print('!!', w)
print('Mode:', 'MINIMAL (login+password)' if MINIMAL else 'LENGKAP')
print('Ringkasan:', ', '.join('%s=%s' % kv for kv in stat.items()))
if DRY_RUN:
    env.cr.rollback()
    print('DRY_RUN: semua perubahan di-ROLLBACK.')
else:
    env.cr.commit()
    print('Tersimpan ke database %s.' % env.cr.dbname)
