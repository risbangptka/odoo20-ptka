# Prompt awal untuk Claude Code

Buka Claude Code di folder `G:\Docker\addons20`, lalu tempel prompt di bawah.
(Supaya Claude Code juga bisa membaca kode Odoo 10, jalankan dengan akses ke `G:\Docker\addons`,
mis. `claude --add-dir G:\Docker\addons`.)

---

Kita mulai pengembangan modul `ka_pkat` (PKAT/EWS di Odoo 20). Jawab dalam Bahasa Indonesia.

Sebelum mengubah apa pun, lakukan ini dan laporkan hasilnya singkat:

1. Baca `CLAUDE.md` di akar repo, lalu `ka_pkat/docs/SRS_v0.1.md` bab 2 s.d. 6 dan bab 12.
2. Baca `ka_base/` (terutama `MIGRASI_ODOO20.md` dan `security/ir.access.csv`) sebagai contoh konvensi Odoo 20
   di repo ini.
3. Periksa lingkungan: container `web_odoo20` berjalan atau tidak, cara repo ini di-mount, dan nama database
   uji yang aman dipakai. Kalau tidak yakin database mana yang boleh dipakai, tanya saya dulu.
   Jangan menyentuh database produksi maupun container Odoo 10.

Lalu kerjakan **Langkah 0** saja:

- Jalankan `python ka_pkat/tests/test_engine.py` dan pastikan 10 test lulus.
- Install `ka_pkat` di database uji Odoo 20. Kerangka ini belum pernah di-install, jadi perbaiki setiap
  error dan warning kompatibilitas (format `ir.access.csv`, `models.Constraint`, definisi grup, view, route
  controller). Untuk setiap perbaikan, cek dulu source core Odoo 20 di container, jangan menebak dari Odoo 17/18.
- Jangan menambah fitur dan jangan mengubah aturan di `services/engine.py` pada langkah ini.
- Setelah install bersih: buka menu PKAT, buat satu Konfigurasi dan satu Token API, panggil
  `POST /api/pkat/v1/ping` dengan token itu, dan tunjukkan hasilnya.

Selesai Langkah 0, berhenti dan berikan:

- daftar perubahan yang kamu buat beserta alasannya,
- hal di `CLAUDE.md` bagian "Konvensi Odoo 20" yang ternyata keliru atau perlu ditambah (perbarui berkasnya),
- usulan rencana Sprint 1 (master + impor PKAT + pembentukan kantung) dalam butir-butir ber-ID SRS,
  untuk saya setujui sebelum dikerjakan.

Commit hasil Langkah 0 dalam satu commit (`[ADD] ka_pkat: kerangka awal ...`), jangan push sebelum saya minta.
