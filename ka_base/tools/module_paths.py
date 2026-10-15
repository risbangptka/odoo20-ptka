"""Helper path fisik berkas di dalam sebuah modul.

Lokasi folder modul berbeda-beda tergantung cara deploy: pada instalasi
Docker modul berada di /mnt/extra-addons, sedangkan pada instalasi biasa
bisa berada di data_dir (~/.local/share/Odoo/addons/<versi>). Karena itu path
modul jangan pernah dituliskan hardcode -- ambil dari addons_path yang
sedang aktif lewat fungsi-fungsi di bawah ini.

Contoh pemakaian::

    from odoo.addons.ka_base.tools import module_dir, module_file

    berkas = module_file('ka_tanaman_pos_pantau', 'security', 'kunci.json')
    folder = module_dir('ka_spt', 'excel')
"""

import logging
import os

from odoo.modules.module import get_module_path

_logger = logging.getLogger(__name__)


def module_path(module, *segments):
    """Path absolut ke `segments` di dalam folder `module`.

    Tidak mengecek apapun ke filesystem, jadi aman dipakai untuk berkas yang
    baru akan dibuat. Mengembalikan None kalau modulnya tidak ada di
    addons_path.
    """
    base = get_module_path(module, display_warning=False)
    if not base:
        _logger.error("Modul '%s' tidak ditemukan di addons_path.", module)
        return None
    return os.path.join(base, *segments)


def module_dir(module, *segments):
    """Path absolut ke sebuah folder di dalam `module`, dibuat kalau belum ada.

    Dipakai sebagai tujuan penulisan berkas. Mengembalikan None kalau modul
    tidak ketemu atau foldernya gagal dibuat.
    """
    path = module_path(module, *segments)
    if not path:
        return None
    try:
        # exist_ok: balapan antar worker aman, folder bisa saja sudah dibuat proses lain.
        os.makedirs(path, exist_ok=True)
    except OSError as e:
        _logger.error("Gagal membuat folder '%s': %s", path, e)
        return None
    return path


def module_file(module, *segments):
    """Path absolut ke sebuah berkas yang harus sudah ada di dalam `module`.

    Dipakai saat membaca berkas. Mengembalikan None -- dan mencatat path yang
    dicari ke log -- kalau berkasnya tidak ditemukan.
    """
    path = module_path(module, *segments)
    if not path:
        return None
    if not os.path.isfile(path):
        _logger.error("Berkas '%s' tidak ditemukan (modul '%s').", path, module)
        return None
    return path
