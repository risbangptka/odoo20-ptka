"""Data dasar bersama untuk test Odoo ka_pkat (dibuat di dalam transaksi test, di-rollback).

Susunan company meniru produksi: satu induk dengan unit-unit sebagai anak, karena kode
account.account Odoo 20 disimpan per company *root* (PERUBAHAN_DESAIN_01 V1).
"""
from odoo.tests.common import TransactionCase, new_test_user


class PkatCase(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        Company = cls.env['res.company']
        cls.group = Company.create({'name': 'Grup Uji PKAT', 'code': 'UJ0'})
        cls.company = Company.create({'name': 'PG Uji PKAT', 'code': 'UJ1', 'parent_id': cls.group.id})
        cls.company_b = Company.create({'name': 'PG Uji PKAT B', 'code': 'UJ2', 'parent_id': cls.group.id})
        companies = cls.company | cls.company_b | cls.group
        cls.env.user.company_ids |= companies
        cls.env = cls.env(context=dict(cls.env.context, allowed_company_ids=companies.ids))
        cls.year = 2031
        cls.dept_pab = cls._department('PAB', 'Pabrikasi')
        cls.dept_ins = cls._department('INS', 'Instalasi')
        cls.seksi_masak = cls._department('PAB-MSK', 'Seksi Masakan', parent_id=cls.dept_pab.id)
        CC = cls.env['pkat.cost.center']
        cls.cc_masak = CC.create({'code': '25', 'name': 'St. Masakan', 'company_id': cls.company.id,
                                  'department_id': cls.dept_pab.id, 'section_id': cls.seksi_masak.id})
        cls.cc_putar = CC.create({'code': '26', 'name': 'St. Putaran', 'company_id': cls.company.id,
                                  'department_id': cls.dept_pab.id})
        cls.cc_ketel = CC.create({'code': '31', 'name': 'St. Ketel', 'company_id': cls.company.id,
                                  'department_id': cls.dept_ins.id})
        cls.acc_masak_brg = cls._account('50250040', 'Bahan Pembantu Masakan')
        cls.acc_masak_upah = cls._account('50250001', 'Upah Masakan', pkat_wage_type='upah')
        cls.acc_putar_brg = cls._account('50260040', 'Bahan Pembantu Putaran')
        cls.acc_ketel_brg = cls._account('50310040', 'Bahan Pembantu Ketel')

    @classmethod
    def _department(cls, code, name, company=None, **kw):
        vals = {'pkat_code': code, 'name': name, 'company_id': (company or cls.company).id}
        vals.update(kw)
        return cls.env['hr.department'].create(vals)

    @classmethod
    def _account(cls, code, name, company=None, **kw):
        """Perkiraan PKAT (account.account, pkat_managed) milik satu unit."""
        company = company or cls.company
        vals = {'code': code, 'name': name, 'account_type': 'expense',
                'company_ids': [(6, 0, company.ids)]}
        vals.update(kw)
        return cls.env['account.account'].with_company(company)._pkat_create([vals])

    @classmethod
    def _user(cls, login, group, companies=None):
        companies = companies or cls.company
        return new_test_user(cls.env, login=login, groups='base.group_user,ka_pkat.%s' % group,
                             company_id=companies[0].id, company_ids=[(6, 0, companies.ids)])
