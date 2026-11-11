# CLAUDE.md — repo `addons20` (modul kustom Odoo 20 PT Kebon Agung)

Jawab dalam **Bahasa Indonesia**. Ringkas; jelaskan risiko dulu; verifikasi sebelum menyatakan selesai.

## Repo ini

- Modul kustom **Odoo 20** (Python 3). Repo pasangan untuk Odoo 10 ada di `G:\Docker\addons`
  (aturan di sana: `Cloude.md`, `PREFERENSI_KERJA_CLAUDE.md`; Python 2.7, jangan pakai sintaks Python 3).
- Container Odoo 20: `web_odoo20` (lihat `ka_base/MIGRASI_ODOO20.md`). Container Odoo 10: `web_odoo10`, DB `230726`.
- Modul yang sudah ada: `ka_base` (sudah di-port), `muk_web_*` (tema pihak ketiga, jangan diubah).

## Konvensi Odoo 20 (contoh nyata: `ka_base`)

Pengetahuan bawaan tentang Odoo 17/18 **belum tentu berlaku**. Bila ragu, baca source core di dalam
container (`docker exec web_odoo20 ...`) dan tiru `ka_base`, jangan menebak.

Butir bertanda ✔ sudah dicek ke source core `odoo:20.0-20260926` dan terbukti saat install `ka_pkat` (11 Nov 2026).

- ✔ ACL: berkas `security/ir.access.csv`, kolom `id,name,model_id,group_id/id,operation,domain`.
  `operation` = subset huruf `crud` (`r`, `ru`, `crud`, …). Model `ir.access` menggabungkan ACL **dan** record
  rule: kolom `domain` diisi = hak hanya untuk record di domain itu. Grup kosong berarti *restriction*
  (mempersempit semua grup), jadi untuk "semua pengguna" pakai `base.group_everyone`.
  Bukan `ir.model.access.csv`, dan tidak ada `ir.rule` terpisah (`base/models/ir_access.py`).
- ✔ `res.groups`: tidak punya `category_id`. Grup dikelompokkan lewat `privilege_id` → `res.groups.privilege`
  (yang punya `category_id` → `ir.module.category`). Form pengguna disusun kategori → privilege → grup, jadi
  **grup tanpa privilege tidak ikut tersusun di sana**. `full_name` = `<privilege> / <nama grup>`: jangan
  awali nama grup dengan nama modul. Anggota: `user_ids` (bukan `users`); di `res.users`: `group_ids`.
  Pola core: grup dasar meng-imply `base.group_user`; grup tertinggi diberi
  `user_ids = base.user_root + base.user_admin` (contoh: `ka_pkat/security/pkat_groups.xml`, `hr/security`).
- ✔ Constraint SQL: `_nama = models.Constraint('unique(...)', 'pesan')` sebagai atribut kelas. Nama constraint
  di DB = `<tabel>_<nama tanpa garis bawah depan>` (mis. `pkat_config_company_year_uniq`).
  `_sql_constraints` **tidak didukung lagi** (hanya memicu warning, constraint tidak dibuat).
  Tersedia juga `models.Index` dan `models.UniqueIndex` (`odoo/orm/table_objects.py`).
- ✔ Controller: `@http.route(..., type='http' | 'jsonrpc')` (bukan `'json'`), `auth='public'|'user'|'bearer'|'none'`,
  `csrf=False` untuk API; `request.make_json_response(body, status=...)` ada. Source ada di paket
  `odoo/http/` (bukan berkas tunggal `http.py`).
- ✔ View: `<list>` (bukan `<tree>`), `invisible="..."` / `readonly="..."` / `column_invisible="1"` berupa ekspresi,
  `<chatter/>`, `view_mode` `list,form,pivot`. URL web client: `/odoo/action-<xmlid>` (mis.
  `/odoo/action-ka_pkat.action_pkat_config/new`).
- `_rec_names_search` + `_compute_display_name` (bukan `name_search` / `name_get`).
- `with_user(user)` (bukan `sudo(user)`); `self.env.uid`.
- Versi manifest `20.0.x.y.z`, lisensi `LGPL-3`.
- Saat `-u` modul ber-`mail.thread`, log INFO "Deleting …message_has_sms_error" itu perilaku core (field milik
  modul `sms` dimuat belakangan dan dibuat ulang); bukan galat modul kita.

## Lingkungan uji (dicek 11 Nov 2026)

- Host Windows **tanpa Python**: semua perintah Python dijalankan di container. Dari Git Bash awali dengan
  `MSYS_NO_PATHCONV=1` (kalau tidak, path `/mnt/...` diubah jadi path Windows).
- Repo ini di-bind-mount ke `/mnt/extra-addons` di `web_odoo20` (image `odoo:20.0-20260926`, port host 9020);
  DB di `db_odoo20` (postgres 18, service `db20`). Konfigurasi: `G:\Docker\config20\odoo.conf`.
- **DB uji: `kebonagung`** (satu-satunya DB Odoo 20; disetujui pemilik untuk install uji `ka_pkat`). Cadangan
  sebelum install pertama: `/tmp/kebonagung_pra_ka_pkat.dump` di dalam `db_odoo20` (hilang bila container dibuat ulang).
- Test engine: `docker exec -w /mnt/extra-addons web_odoo20 python3 ka_pkat/tests/test_engine.py`
- Upgrade: `docker exec web_odoo20 odoo -c /etc/odoo/odoo.conf -d kebonagung -u ka_pkat --stop-after-init --no-http`
  lalu `docker restart web_odoo20` (server live tidak memuat ulang kode Python). Periksa keluaran selain `INFO`;
  warning `markdown2 is not installed` berasal dari image, abaikan.
- Akun uji UI: `pkat_uji` (grup Administrator PKAT, semua company); sandinya di `.pkat_uji_login.local`
  (tidak di-commit). Token API uji dibuat dari menu PKAT → Konfigurasi → Token API; kode company = `res.company.code`
  (`1` Kantor Direksi, `2` PG Kebon Agung, `4` PG Trangkil).
- Browser pane Claude harus **terlihat** saat uji UI; kalau tersembunyi web client Odoo tidak ter-render.

## Proyek aktif: PKAT / EWS (P001-26)

Modul anggaran `ka_logistik_pkrat` + `ka_stock_account_pkrat` (Odoo 10) dibangun ulang di Odoo 20 sebagai
**`ka_pkat`**: pusat anggaran. Modul transaksi (SPM, PO, bon, faktur, kas/bank, jurnal) **tetap di Odoo 10** dan
memanggil Odoo 20 lewat API melalui modul penghubung baru **`ka_pkat_connector`** (di repo Odoo 10, belum dibuat).

Dokumen acuan (urutan prioritas bila bertentangan: hasil rapat/BRD > SRS > Pedoman):

| Dokumen | Lokasi |
|---|---|
| SRS v0.1 (teks) | `ka_pkat/docs/SRS_v0.1.md` — **baca bab 3, 4, 5, 6 sebelum koding** |
| SRS / BRD v1.0 (Word, resmi) | `E:\PB.01.02 SOFTWARE\PB.01.02.01 ODOO\99. Pengembangan\16. EWS dan Realisasi Anggaran\` |
| Kode lama sebagai referensi perilaku | `G:\Docker\addons\ka_logistik_pkrat`, `ka_stock_account_pkrat`, `ka_logistik_spm`, `ka_purchase`, `ka_spk` (+ `AUDIT_*.md` tiap modul) |

Setiap spesifikasi punya ID (`FS-CK-05`, `API-04`, `AD-03`, …). **Cantumkan ID itu di commit dan komentar kode.**

### Aturan inti yang tidak boleh dilanggar

1. **Satu pengambil keputusan**: lolos/peringatan/tolak dihitung di Odoo 20. Aturannya ada di
   `ka_pkat/services/engine.py` (Python murni, ada unit test). Ubah aturan → ubah test dulu.
2. **SPM/SPPJ hanya peringatan**; **PO ditolak** bila serapan kantung > 100%; **bon/BA-NTB/kas-bank/memo ditolak**
   bila realisasi kantung > 100%. Tepat 100% boleh. Perkiraan tanpa anggaran ditolak.
   Perkiraan sendiri > 100% tapi kantung cukup → peringatan saja.
3. **Serapan** = Σ PO terkonfirmasi tanpa PPN; berkurang hanya bila PO dibatalkan. PO PLB juga menambah
   serapan perkiraan biaya rutin. **Realisasi** = jurnal posted; realisasi proyek hanya debit kecuali jurnal `Kor.`.
4. **Kantung**: tingkat `account` / `cost_center` / `department` (bawaan bagian), dipisah upah / non-upah.
   **Dasar kunci**: `yearly` / `ytd` / `mtd` (bawaan yearly). Keduanya diatur Bagian Anggaran Kantor Direksi.
5. **Tidak ada unlock manual / bypass.** Kunci terbuka hanya lewat pergeseran/tambahan yang disetujui.
   (Kunci *manual* oleh Bagian Anggaran boleh: LK-04.) Tebu SPT (`is_spt`) tidak dikunci, tidak ikut pergeseran.
6. **Atomik + idempoten**: cek PO dan pencatatan serapan dalam satu transaksi dengan `FOR UPDATE` pada
   `pkat.pocket` / `pkat.project`; setiap operasi membawa `X-Idempotency-Key`.
7. **Fail-closed**: Odoo 20 tidak terjangkau → PO dan transaksi realisasi di Odoo 10 ditolak; SPM tetap jalan bertanda.
8. Tahun/bulan anggaran dari **tanggal dokumen**, bukan tanggal sistem. Pertukaran data pakai **kode**, bukan id.
9. Keamanan: semua model ber-`company_id`; tidak ada ACL tanpa grup; tanpa `sudo()` untuk membaca anggaran di luar
   controller API; SQL selalu berparameter; token API disimpan ter-hash; tidak ada endpoint generik.
10. Jangan mengulang temuan audit modul lama (lihat BRD Lampiran B / `AUDIT_ka_logistik_pkrat.md`):
    cron hitung realisasi, analytic tanpa company, `sudo()` polos, tanggal sistem.

### Status `ka_pkat` (Langkah 0 selesai, 11 Nov 2026)

**Sudah ter-install bersih di DB `kebonagung`** (tanpa error/warning dari `ka_pkat`): 20 model, 13 constraint,
50 baris `ir.access`, 7 grup + privilege "PKAT", 27 view, 23 menu. `tests/test_engine.py` lulus (10 test).
Teruji lewat UI: buat Konfigurasi, buat Token API, `POST /api/pkat/v1/ping` → 200 `OK`; token salah / company
lain → 401; layanan lain → 501 dan tercatat di `pkat.api.log`. Semua action memuat view-nya dari sisi server
(`get_views`); layar selain Konfigurasi dan Token **belum** dibuka satu per satu di browser.

Celah yang diketahui (bukan lingkup Langkah 0): grup `pkat_api` (SRS 2.3) belum ada; panggilan API yang gagal
autentikasi belum dicatat (API-G-08); belum ada domain company/area di `ir.access` (AK-01, AK-02).

| Bagian | Isi | Status |
|---|---|---|
| `models/` | 15+ model sesuai SRS bab 3 (DM-01 … DM-15) + `pkat.api.token` | Field lengkap; logika sebagian `TODO` |
| `services/engine.py` | Aturan keputusan FS-CK-01 … FS-CK-11, jendela yearly/ytd/mtd, warna EWS | **Selesai + teruji** |
| `controllers/main.py` | Rute API-01 … API-11, autentikasi token, log | Hanya `ping` berfungsi; lainnya 501 |
| `security/` | privilege "PKAT" + 7 grup + `ir.access.csv` | Belum ada domain company/area (AK-01, AK-02) |
| `views/` | List/form + menu (SRS 7.1) | Dashboard dan laporan belum ada |
| `TODO` utama | `pkat.pocket._rebuild_*` / `_find_for_line`, `pkat.change.request._apply` / `_validate`, carry over, impor Excel | Belum |

### Urutan kerja yang disarankan

0. ~~**Install kerangka** di DB uji, perbaiki kompatibilitas Odoo 20, jalankan test.~~ **Selesai 11 Nov 2026.**
1. **Sprint 1** — master + impor PKAT (FS-PK-01…09), pembentukan kantung (DM-07, FS-CK-04), record rule company/area.
2. **Sprint 2** — lapisan layanan di atas engine: API-04/05 (serapan PO, atomik, idempoten), API-07 (jurnal),
   API-02/03, API-08/09/11; lalu `ka_pkat_connector` di Odoo 10 (bab 6, AD-01…AD-10).
3. **Sprint 3** — API-06 (cek realisasi), penguncian + notifikasi (FS-LK), pergeseran & tambahan (FS-SW, FS-TA), investasi.
4. **Sprint 4** — dashboard 4 tab, laporan UI-LP-01…05, migrasi (bab 10), skenario SIT TS-01…TS-17.

### Cara kerja

- Verifikasi tiap perubahan: `python -m py_compile`, validasi XML, upgrade modul one-off di container, jalankan test.
  Test engine tanpa Odoo: `python ka_pkat/tests/test_engine.py`.
- Commit kecil per ID spesifikasi; pesan commit gaya repo (`[ADD]`, `[FIX]`, `[MIG]`) + ID SRS.
- **Asumsi desain yang belum dikonfirmasi tim ada di SRS bab 12** (nilai bon = kuantum × harga standar, PO antar-company
  dicatat sekali, revisi PO = batal + terbit ulang, `ka_logistik_pkrat` jadi cermin baca-saja, dll.).
  Bila pekerjaan menyentuh salah satunya, **tanyakan dulu**, jangan diputuskan sendiri.
- Perubahan di repo Odoo 10 selain modul baru `ka_pkat_connector` (mis. mengubah `ka_logistik_spm`, `ka_purchase`):
  tunjukkan rencana dan minta persetujuan dulu. Jangan sentuh data produksi.
- Bila SRS dan kode lama berbeda, SRS yang berlaku; bila SRS tidak mengatur, tanyakan.
