"""DM-01: konfigurasi PKAT per company dan tahun."""
from unittest.mock import patch

from odoo.exceptions import AccessError
from odoo.tests import tagged

from .common import PkatCase


@tagged('post_install', '-at_install')
class TestConfig(PkatCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.config = cls.env['pkat.config'].create({'company_id': cls.company.id, 'year': cls.year})
        cls.user_kd = cls._user('uji_kd', 'group_pkat_anggaran_kd')
        cls.user_tuk = cls._user('uji_tuk', 'group_pkat_tuk_unit')

    def test_bawaan(self):
        self.assertEqual(self.config.pocket_level, 'department')
        self.assertEqual(self.config.lock_basis, 'yearly')
        self.assertEqual((self.config.ews_yellow, self.config.ews_red), (75.0, 100.0))
        self.assertTrue(self.config.lock_active)

    def test_hanya_anggaran_kd_yang_mengubah(self):
        with self.assertRaises(AccessError):
            self.config.with_user(self.user_tuk).write({'lock_basis': 'ytd'})
        with self.assertRaises(AccessError):
            self.config.with_user(self.user_tuk).write({'pocket_level': 'account'})
        self.config.with_user(self.user_kd).write({'lock_basis': 'ytd'})
        self.assertEqual(self.config.lock_basis, 'ytd')

    def test_rebuild_hanya_saat_pocket_level_berubah(self):
        Pocket = type(self.env['pkat.pocket'])
        with patch.object(Pocket, '_rebuild_for_configs', autospec=True) as rebuild:
            self.config.with_user(self.user_kd).write({'lock_basis': 'mtd'})
            self.config.with_user(self.user_kd).write({'pocket_level': 'department'})  # nilai sama
            rebuild.assert_not_called()
            self.config.with_user(self.user_kd).write({'pocket_level': 'cost_center'})
            rebuild.assert_called_once()
            self.assertEqual(rebuild.call_args[0][1], self.config)

    def test_perubahan_tercatat_di_chatter(self):
        self.config.with_user(self.user_kd).write({'pocket_level': 'account', 'lock_basis': 'ytd'})
        self.env.flush_all()
        self.cr.flush()  # tracking ditulis saat precommit
        # Odoo 20: tidak ada mail.tracking.value; nilai lama -> baru ditulis di body
        # mail.message bertipe 'tracking' ("lama → <b>baru</b> <i>(Label field)</i>").
        tracked = self.env['mail.message'].search([
            ('model', '=', 'pkat.config'), ('res_id', '=', self.config.id),
            ('message_type', '=', 'tracking')])
        self.assertEqual(len(tracked), 1)
        self.assertEqual(tracked.author_id, self.user_kd.partner_id)
        body = str(tracked.body)
        for lama, baru, label in (('Bagian', 'Perkiraan', 'Tingkat Kantung'),
                                  ('Tahunan (yearly)', 'S.d. bulan berjalan (year to date)',
                                   'Dasar Penguncian')):
            self.assertRegex(body, r'%s\s*→\s*<b>%s</b>\s*<i>\(%s\)</i>' % (
                lama.replace('(', r'\(').replace(')', r'\)'),
                baru.replace('(', r'\(').replace(')', r'\)'), label))
