# Perubahan Desain 01 — Perkiraan dan barang memakai modul bawaan Odoo 20

Tanggal: 11 November 2026. Sumber: keputusan pemilik proyek (Danes) setelah meninjau format impor Odoo 10.

Dokumen ini **mengungguli SRS v0.1** pada butir yang disebut di bawah. SRS v0.2 menyusul setelah
"Langkah V" (verifikasi) selesai. Aturan bisnis BRD v1.0 tidak berubah.

## 1. Keputusan

| ID | Keputusan | Mengganti di SRS v0.1 |
|---|---|---|
| K1 | Master perkiraan = `account.account` Odoo 20 (modul `account`), diperluas dengan field PKAT. Model `pkat.account` dihapus. Polanya sama dengan Odoo 10 (`logistik.pkrat.account.account_id` → `account.account`, field stasiun/bagian di perkiraan). | DM-02, MG-03 |
| K2 | Master barang = `product.product` Odoo 20 (modul Inventory/`stock`). Tidak ada model barang buatan sendiri. | (baru) |
| K3 | Perkiraan Odoo 20 terhubung satu-satu dengan perkiraan Odoo 10. Kunci: kode company + kode perkiraan. Selama transaksi akuntansi masih di Odoo 10, **Odoo 10 adalah sumber data**; Odoo 20 menerima lewat sinkronisasi master (API-08). Hal yang sama berlaku untuk barang (kunci: `default_code`). | FS-PK-09, API-08 |
| K4 | Impor PKAT memakai 4 berkas format Odoo 10 apa adanya, dan rincian disimpan lengkap (barang per produk, uraian non-barang, upah). | FS-PK-01, FS-PK-02 |
| K5 | Kode perkiraan berpola `NNNN.NNN` atau `NNNN.NNNN` (77 dari 4.572 baris berkas 2025 memakai 4 digit di belakang titik). Stasiun = digit 3–4; jenis biaya = karakter 7–8. Tidak ada validasi "8 digit". | DM-02 |
| K6 | Realisasi tetap dicatat di `pkat.realization` dari jurnal Odoo 10 lewat API. **Tidak membuat `account.move` di Odoo 20** (menghindari pembukuan ganda). Karena perkiraan sudah `account.account`, kelak bila akuntansi pindah ke Odoo 20 realisasi bisa dibaca langsung dari jurnal tanpa mengubah master. | (penegasan) |

Tidak berubah: `pkat.department` dan `pkat.cost.center` tetap model sendiri (kecuali pemilik memutuskan lain,
lihat pertanyaan P1), mesin aturan `services/engine.py`, kantung, API cek transaksi.

## 2. Langkah V — verifikasi dulu, jangan menebak

Periksa di source core Odoo 20 di container, lalu laporkan sebelum mengubah kode:

1. `account.account`: apakah satu perkiraan bisa dipakai banyak company (`company_ids`) dan apakah `code`
   bergantung company. Odoo 10 menyimpan satu record per company. Usulkan cara menjaga hubungan satu-satu
   (usulan awal: satu record per company, `company_ids` berisi tepat satu company).
2. `account.account`: field wajib (`account_type` dsb.), batasan format/keunikan `code`, apakah kode bertitik
   seperti `5010.4441` diterima, dan apakah masih ada hierarki induk. Odoo 10 punya `parent_id` dan
   perkiraan non-detail (`is_detail = False`).
3. Pemetaan `user_type_id` Odoo 10 → tipe perkiraan Odoo 20. Daftar tipe yang dipakai diambil dari
   `G:\Docker\addons\ka_account` (baca saja).
4. `product.product`/`product.template`: field wajib, keunikan `default_code`, satuan (`uom`). Cek apakah
   kode barang Odoo 10 unik lintas company (wizard lama mencari tanpa filter company).
5. Dampak meng-install `account` dan `stock` di DB `kebonagung` (menu, data bawaan, chart of accounts yang
   ikut terpasang). **Backup DB sebelum install; minta persetujuan pemilik sebelum menjalankannya.**
6. Field perkiraan di Odoo 10 yang dipakai PKAT: `stasiun_id`, `bagian_id`, `upah`, `sarmut_id`, `lrb_id`,
   `is_detail` (`ka_account/models/account.py`, `ka_logistik_pkrat/models/logistik_pkrat_account.py`).

## 3. Pekerjaan setelah Langkah V disetujui

1. Manifest: `depends` ditambah `account` dan `stock`.
2. `account.account` di-inherit dengan field berawalan `pkat_`: stasiun (`pkat.cost.center`), bagian
   (`pkat.department`), jenis upah/non-upah, kelompok, kantung unit, tanda Tebu SPT, tanda perlu dilengkapi,
   jenis biaya (terhitung), dan `ka10_id` (id perkiraan di Odoo 10, untuk penelusuran).
3. Semua relasi ke `pkat.account` dipindah ke `account.account`; model, view, akses, dan test lama disesuaikan.
   Commit `e15ebe0` dan `f038160` terdampak; logikanya dipertahankan, hanya pindah model.
4. Rincian anggaran, mengikuti Odoo 10 (`logistik.pkrat.barang`, `.uraian`, `.upah`, `.bulan`):
   barang (produk, jumlah, harga), uraian non-barang (uraian, tiga pasang jumlah/satuan, harga), upah
   (uraian, jumlah). Nilai komponen per perkiraan dihitung dari rincian. Rumus mengikuti kode Odoo 10.
5. Impor 4 berkas, kolom persis format lama:
   - A4: `ACCOUNT, JAN..DES` (tahun dan unit dipilih di wizard)
   - BARANG: `ACCOUNT, BARANG, HARGA, SATUAN` (tahun, unit, bagian di wizard)
   - NON BARANG: `ACCOUNT, URAIAN, JUMLAH-1, SATUAN-1, JUMLAH-2, SATUAN-2, JUMLAH-3, SATUAN-3, HARGA`
   - UPAH: `ACCOUNT, URAIAN, JUMLAH`

   Kolom lain diabaikan. Perbaikan dibanding wizard lama: semua baris diperiksa dulu baru disimpan, data lama
   tidak dihapus sebelum lolos validasi, daftar baris gagal bisa diunduh, sel kode barang/perkiraan yang
   berformat angka ditolak dengan pesan jelas (`3637.010` terbaca `3637.01`).
6. Master awal Sprint 1: perkiraan dan barang dimuat sekali dari ekspor Odoo 10 (berkas, bukan koneksi
   langsung ke DB Odoo 10). Sinkronisasi otomatis (API-08, ditambah jenis data barang) tetap di Sprint 2.
7. Uji dengan berkas 2025 di `E:\...\16. EWS dan Realisasi Anggaran\UPLOAD ODOO`. Laporkan apakah total A4
   per perkiraan = barang + non-barang + upah; hasilnya menentukan nasib aturan "Σ bulanan = Σ komponen"
   di FS-PK-02.

## 4. Batasan

- Perkiraan dan barang tidak dibuat manual di Odoo 20 selama Odoo 10 masih sumber data (cegah dua sumber).
- Tidak ada transaksi stok atau jurnal di Odoo 20 dalam proyek ini; hanya masternya yang dipakai.
- Rincian barang untuk rujukan dan laporan. Pemeriksaan anggaran tetap di tingkat kantung (BRD v1.0).
- Tidak ada panggilan dari Odoo 20 ke Odoo 10; arah komunikasi tetap Odoo 10 → Odoo 20.

## 5. Pertanyaan untuk pemilik (jangan diputuskan sendiri)

- P1. Bagian/seksi: tetap `pkat.department`, atau ikut Odoo 10 memakai `hr.department` (menambah modul `hr`)?
- P2. Perkiraan non-detail/induk Odoo 10: ikut disinkronkan atau hanya perkiraan detail?
- P3. Hasil butir 7 bila total A4 ≠ jumlah komponen di data 2025.
