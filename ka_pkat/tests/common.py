"""Data dasar bersama untuk test Odoo ka_pkat (dibuat di dalam transaksi test, di-rollback)."""
from odoo.tests.common import TransactionCase, new_test_user


class PkatCase(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        Company = cls.env['res.company']
        cls.company = Company.create({'name': 'PG Uji PKAT', 'code': 'UJ1'})
        cls.company_b = Company.create({'name': 'PG Uji PKAT B', 'code': 'UJ2'})
        cls.year = 2031
        Dept = cls.env['pkat.department']
        cls.dept_pab = Dept.create({'code': 'PAB', 'name': 'Pabrikasi', 'company_id': cls.company.id})
        cls.dept_ins = Dept.create({'code': 'INS', 'name': 'Instalasi', 'company_id': cls.company.id})
        cls.seksi_masak = Dept.create({'code': 'PAB-MSK', 'name': 'Seksi Masakan',
                                       'company_id': cls.company.id, 'parent_id': cls.dept_pab.id})
        CC = cls.env['pkat.cost.center']
        cls.cc_masak = CC.create({'code': '25', 'name': 'St. Masakan', 'company_id': cls.company.id,
                                  'department_id': cls.dept_pab.id, 'section_id': cls.seksi_masak.id})
        cls.cc_putar = CC.create({'code': '26', 'name': 'St. Putaran', 'company_id': cls.company.id,
                                  'department_id': cls.dept_pab.id})
        cls.cc_ketel = CC.create({'code': '31', 'name': 'St. Ketel', 'company_id': cls.company.id,
                                  'department_id': cls.dept_ins.id})
        cls.acc_masak_brg = cls._account('50250040', 'Bahan Pembantu Masakan')
        cls.acc_masak_upah = cls._account('50250001', 'Upah Masakan', wage_type='upah')
        cls.acc_putar_brg = cls._account('50260040', 'Bahan Pembantu Putaran')
        cls.acc_ketel_brg = cls._account('50310040', 'Bahan Pembantu Ketel')

    @classmethod
    def _account(cls, code, name, **kw):
        vals = {'code': code, 'name': name, 'company_id': cls.company.id}
        vals.update(kw)
        return cls.env['pkat.account'].create(vals)

    @classmethod
    def _user(cls, login, group, companies=None):
        companies = companies or cls.company
        return new_test_user(cls.env, login=login, groups='base.group_user,ka_pkat.%s' % group,
                             company_id=companies[0].id, company_ids=[(6, 0, companies.ids)])
