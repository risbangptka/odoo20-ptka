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
| K5 | Kode perkiraan berpola `NNNN.NNN` atau `NNNN.NNNN` (77 dari 4.572 baris berkas 2025 memakai 4 digit di belakang titik). Stasiun = 4 karakter pertama kode (dikoreksi setelah Langkah V; "digit 3–4" di SRS v0.1 keliru); karakter ke-6 = kode unit; jenis biaya = karakter 7–8. Tidak ada validasi "8 digit". | DM-02 |
| K6 | Realisasi tetap dicatat di `pkat.realization` dari jurnal Odoo 10 lewat API. **Tidak membuat `account.move` di Odoo 20** (menghindari pembukuan ganda). Karena perkiraan sudah `account.account`, kelak bila akuntansi pindah ke Odoo 20 realisasi bisa dibaca langsung dari jurnal tanpa mengubah master. | (penegasan) |

| K7 | Bagian/seksi/sub seksi = `hr.department` Odoo 20 (modul `hr`), seperti Odoo 10. Model `pkat.department` dihapus. Kunci tautan ke Odoo 10: kode company + id/nama departemen Odoo 10 (disimpan di `ka10_id`). Diputuskan pemilik 11 Nov 2026. | DM-02, AK-02 |
| K8 | Perkiraan induk (non-detail) Odoo 10 ikut disinkronkan, lengkap dengan hubungan induk-anak. Perkiraan induk tidak boleh dianggarkan dan tidak membentuk kantung. Diputuskan pemilik 11 Nov 2026. | DM-02, FS-PK-09 |

Tidak berubah: `pkat.cost.center` (stasiun) tetap model sendiri, padanan `ka_account.stasiun` Odoo 10, dengan
bagian/seksi/sub seksi menunjuk ke `hr.department`; mesin aturan `services/engine.py`; kantung; API cek transaksi.

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
5. Dampak meng-install `account`, `stock`, dan `hr` di DB `kebonagung` (menu, data bawaan, chart of accounts yang
   ikut terpasang). **Backup DB sebelum install; minta persetujuan pemilik sebelum menjalankannya.**
6. `hr.department`: field wajib, hierarki (`parent_id`), dan `manager_id`. Di Odoo 10 kepala bagian adalah
   pegawai (`hr.employee`). Lingkup area (AK-02) butuh **pengguna**, sedangkan master pegawai belum
   disinkronkan. Usulan awal: field `pkat_manager_user_id` di `hr.department` supaya tidak perlu memindahkan
   data pegawai; laporkan bila ada cara yang lebih baik. Cek juga `ka_account.bagian` Odoo 10 (kode bagian).
7. Hierarki perkiraan (K8): bila `account.account` Odoo 20 tidak punya induk, usulkan cara menyimpannya
   (misalnya field `pkat_parent_id` dan tanda `pkat_is_detail`), dan cara mencegah perkiraan induk dipakai
   transaksi.
8. Field perkiraan di Odoo 10 yang dipakai PKAT: `stasiun_id`, `bagian_id`, `upah`, `sarmut_id`, `lrb_id`,
   `is_detail` (`ka_account/models/account.py`, `ka_logistik_pkrat/models/logistik_pkrat_account.py`).

## 3. Pekerjaan setelah Langkah V disetujui

1. Manifest: `depends` ditambah `account`, `stock`, dan `hr`.
2. `account.account` di-inherit dengan field berawalan `pkat_`: stasiun (`pkat.cost.center`), bagian
   (`hr.department`), induk dan tanda detail (K8), jenis upah/non-upah, kelompok, kantung unit, tanda Tebu SPT, tanda perlu dilengkapi,
   jenis biaya (terhitung), dan `ka10_id` (id perkiraan di Odoo 10, untuk penelusuran).
3. Semua relasi ke `pkat.account` dipindah ke `account.account` dan relasi ke `pkat.department` dipindah ke
   `hr.department` (termasuk `pocket_level = department` dan domain area di `ir.access`); model, view, akses, dan test lama disesuaikan.
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
6. Master awal Sprint 1: perkiraan (termasuk induk), bagian, stasiun, dan barang dimuat sekali dari ekspor Odoo 10 (berkas, bukan koneksi
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

- P1. (terjawab, lihat K7)
- P2. (terjawab, lihat K8)
- P3. Hasil butir 7 bila total A4 ≠ jumlah komponen di data 2025.

## 6. Keputusan setelah Langkah V (11 November 2026)

Hasil Langkah V diterima. Rancangan field dan relasi yang diusulkan disetujui dengan ketentuan berikut.

| ID | Ketentuan |
|---|---|
| V1 | Satu record `account.account` per unit, `company_ids` berisi tepat satu company, `pkat_company_id` tersimpan, unik (`pkat_company_id`, `code`) dan (`pkat_company_id`, `ka10_id`). Sebelum memuat master, **uji** bahwa dua unit bersaudara boleh punya kode sama; bila core menolak, berhenti dan laporkan. |
| V2 | Stasiun perkiraan = 4 karakter pertama kode, sama dengan Odoo 10. Validasi "digit 3–4" di commit `e15ebe0` diperbaiki. |
| V3 | Perkiraan induk (tipe View Odoo 10) disinkronkan memakai `parent_id` bawaan, ditandai `pkat_is_view`. Tidak boleh dianggarkan, tidak membentuk kantung. `account_type`-nya diisi dari tipe anak terbanyak; jangan pernah `asset_cash` atau `liability_credit_card`. Tipe Un-Postable diperlakukan sama. |
| V4 | Memuat/menyinkronkan perkiraan **tidak boleh membuat jurnal otomatis** (perkiraan kas/bank, kartu kredit). Pakai mekanisme core yang terverifikasi dan buktikan dengan test: jumlah `account.journal` sebelum = sesudah. |
| V5 | Kolom tipe perkiraan (`user_type_id`) wajib ada di ekspor master Odoo 10. Tipe yang tidak ada di tabel pemetaan: baris ditolak dengan alasan, bukan ditebak. |
| V6 | Barang: kunci `default_code`; unik di antara barang `pkat_managed`. Satuan dipadankan lewat **tabel padanan yang disetujui pemilik**; satuan tanpa padanan dilaporkan dulu, tidak dibuat otomatis. |
| V7 | Pemeriksaan total bulanan = total komponen **tidak** dilakukan saat impor (empat berkas diimpor terpisah). Dilakukan saat pengajuan, pembulatan 2 desimal, sama dengan Odoo 10 dan FS-PK-06. Kalimat itu dicabut dari FS-PK-02. P3 selesai. |
| V8 | Rumus rincian mengikuti Odoo 10: barang = jumlah rencana × harga (kolom `SATUAN` = jumlah rencana, > 0); non-barang = harga × tiap jumlah yang tidak nol, dibagi 100 bila satuannya `%`; upah dan bulanan nilai langsung; komponen proyek dari investasi, bukan dari impor. |
| V9 | Kode bagian (`ka_account.bagian.kode` Odoo 10) disimpan sebagai field di `hr.department`, tanpa model pembungkus. |
| V10 | **Diputuskan pemilik 11 Nov 2026: diperbaiki di Odoo 20.** Upah/non-upah dihitung dari jenis biaya = karakter 7–8 kode, untuk kode 8 maupun 9 karakter (`5022.4031` → jenis `03` → upah). Kejanggalan pemotongan kode Odoo 10 tidak ditiru; Odoo 10 tidak diubah. Aturan rentang upah lainnya mengikuti Odoo 10 (jenis biaya 00–07, atau 4 karakter pertama `4001`). Saat memuat master, hasilkan daftar perkiraan yang jenis upahnya berbeda dari Odoo 10 (perkiraan, nama, unit, nilai Odoo 10, nilai Odoo 20) untuk dikonfirmasi Bagian Anggaran. |

Masih harus dilaporkan sebelum bagian 3 dikerjakan: temuan `hr.department` (Langkah V butir 6: terpasang atau
belum, field wajib, kepala bagian), isi "P4" yang disebut di laporan, daftar berkas/commit terdampak, dan
rencana Sprint 1 hasil revisi. V10 sudah diputuskan.

## 7. Jawaban atas pertanyaan P1–P6 dan catatan rencana Sprint 1 revisi (11 November 2026)

| Pertanyaan | Jawaban |
|---|---|
| P1 | Selesai: `hr.department` (K7). |
| P2 | Selesai: perkiraan induk disinkronkan (K8, V3). |
| P3 | Selesai: pemeriksaan total saat pengajuan, bukan saat impor (V7). Uji berkas 2025 tetap dilaporkan sebagai informasi. |
| P4 | Un-Postable tetap disinkronkan (K3: semua perkiraan Odoo 10 punya pasangan), ditandai dan tidak boleh dianggarkan, sama dengan perkiraan induk (V3). |
| P5 | Kode stasiun = 4 karakter pertama, mis. `5010` (V2). |
| P6 | **Tidak** diambil apa adanya dari Odoo 10. Dihitung di Odoo 20 dari karakter 7–8 (V10, keputusan pemilik), dengan daftar selisih terhadap Odoo 10. |

Tambahan untuk rencana Sprint 1 revisi (urutan lain disetujui):

- Butir 1 mencakup juga K7 (`pkat.department` → `hr.department`, kode bagian V9, penanggung jawab area) dan
  K8/V3 (perkiraan induk). Temuan `hr.department` dari Langkah V butir 6 **belum dilaporkan**; laporkan dulu.
- Butir 1 atau 5 memuat uji V1 (kode sama pada dua unit bersaudara) dan V4 (tidak ada jurnal otomatis).
- Butir 5 menghasilkan daftar selisih upah/non-upah (V10) dan daftar satuan tanpa padanan (V6).
- Berkas ekspor master Odoo 10 disediakan pemilik. Tidak ada akses ke database atau container Odoo 10 tanpa
  izin tertulis pemilik di percakapan.
