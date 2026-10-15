"""Migrasi ka_base dari Odoo 10 (versi 10.0.0.1).

KB-02: di Odoo 10 data induk KA dibuat dengan xmlid base.xxx. Odoo 20 tidak
mengizinkan modul membuat record atas nama modul lain, jadi xmlid tersebut
dipindah ke ka_base.xxx sebelum data/ka_base_data.xml dimuat. Tanpa ini,
update modul akan membuat partner/company/user DUPLIKAT.
"""
import logging

_logger = logging.getLogger(__name__)

KA_XMLIDS = (
    'ou_direksi', 'ou_kebonagung', 'ou_trangkil',
    'kantor_direksi', 'pg_kebonagung', 'pg_trangkil',
    'user_direksi', 'user_kebonagung', 'user_trangkil',
    'user_automated_direksi', 'user_automated_kebonagung', 'user_automated_trangkil',
)


def migrate(cr, version):
    if not version:
        return
    cr.execute("""
        UPDATE ir_model_data old
           SET module = 'ka_base'
         WHERE old.module = 'base'
           AND old.name IN %s
           AND NOT EXISTS (
                SELECT 1 FROM ir_model_data new
                 WHERE new.module = 'ka_base' AND new.name = old.name)
     RETURNING old.name
    """, (KA_XMLIDS,))
    moved = [row[0] for row in cr.fetchall()]
    _logger.info("ka_base: %d xmlid dipindah dari base ke ka_base: %s", len(moved), ', '.join(sorted(moved)))
