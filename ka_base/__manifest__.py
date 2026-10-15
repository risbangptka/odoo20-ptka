{
    'name': "KA Base Setting",
    'summary': "Modul Dasar untuk PT. Kebon Agung",
    'description': """
Modul fondasi multi-company PT. Kebon Agung (port dari Odoo 10).

1. res.company : code, intercompany_user_id (user R/K otomatis),
   internal_user_id, automated_system_user_id; tampil sebagai "code nama".
2. res.partner : is_operating_unit (penanda Unit/PG untuk jurnal R/K), new_city.
3. res.users   : default_operating_unit_id, operating_unit_ids.
4. res.city.state : master kota/kabupaten.
5. res.country.state : field active (arsip provinsi).
6. tools.module_paths : helper path berkas modul tanpa hardcode.
    """,
    'author': "PT. Kebon Agung",
    'website': "http://www.ptkebonagung.com",
    'category': 'Hidden',
    'version': '20.0.1.0.0',
    'license': 'LGPL-3',
    'depends': ['base'],
    'data': [
        'security/ir.access.csv',
        'views/res_partner_view.xml',
        'views/res_company_view.xml',
        'views/res_user_view.xml',
        'views/res_country_state_view.xml',
        'data/ka_base_data.xml',
    ],
    'installable': True,
}
