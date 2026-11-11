{
    'name': "KA PKAT - Pengendalian & Monitoring Anggaran",
    'summary': "Pusat anggaran PKAT, EWS, serapan/realisasi, dan API untuk Odoo 10",
    'description': """
Modul PKAT Odoo 20 (pengganti ka_logistik_pkrat + ka_stock_account_pkrat Odoo 10).

Acuan: BRD v1.0 (21 Okt 2026) dan SRS v0.1 (10 Nov 2026) proyek P001-26.
Lihat CLAUDE.md di akar repo untuk ringkasan desain dan status pengerjaan.

KERANGKA AWAL - sudah ter-install bersih di Odoo 20 (Langkah 0, 11 Nov 2026);
logika bisnis sebagian besar masih TODO.
    """,
    'author': "PT. Kebon Agung",
    'website': "http://www.ptkebonagung.com",
    'category': 'Accounting',
    'version': '20.0.0.1.0',
    'license': 'LGPL-3',
    'depends': ['base', 'mail', 'ka_base'],
    'data': [
        'security/pkat_groups.xml',
        'security/ir.access.csv',
        'data/ir_sequence.xml',
        'views/pkat_config_views.xml',
        'views/pkat_master_views.xml',
        'views/pkat_budget_views.xml',
        'views/pkat_project_views.xml',
        'views/pkat_pocket_views.xml',
        'views/pkat_change_request_views.xml',
        'views/pkat_ledger_views.xml',
        'views/pkat_log_views.xml',
        'views/pkat_menus.xml',
    ],
    'application': True,
    'installable': True,
}
