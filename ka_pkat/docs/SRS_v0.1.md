# SRS v0.1 - Penambahan dan Perbaikan Pengendalian & Monitoring Anggaran (EWS & PKAT)

> Ekspor teks dari `03. SRS EWS dan Realisasi Anggaran v0.1.docx` (10 Nov 2026) untuk dibaca di editor/Claude Code.
> Sumber resmi tetap berkas Word di folder proyek `16. EWS dan Realisasi Anggaran`. Perbarui berkas ini bila SRS direvisi.

## 1. Pendahuluan

### 1.1 Tujuan Dokumen

Software Requirement Specification (SRS) ini menjabarkan spesifikasi perangkat lunak untuk proyek **Penambahan dan Perbaikan Pengendalian & Monitoring Anggaran** (EWS dan PKAT), sebagai turunan teknis dari **BRD versi 1.0** tanggal 21 Oktober 2026. BRD menjawab apa yang dibutuhkan bisnis; SRS ini menjawab bagaimana sistem dibangun: struktur data, aturan proses, antarmuka (API) Odoo 10 ↔ Odoo 20, layar, hak akses, migrasi, dan pengujian.

Dokumen ini menjadi acuan tim PDE (System Analyst, Developer, QA) untuk desain rinci, pengembangan, SIT, dan penyusunan skenario UAT. Setiap spesifikasi mencantumkan ID kebutuhan BRD yang dipenuhinya (kolom Ref. BRD); matriks lengkap ada di Lampiran A.

### 1.2 Ruang Lingkup Perangkat Lunak

> • **Modul PKAT di Odoo 20** (ka_pkat): data anggaran, kantung, buku serapan dan realisasi, mesin pemeriksaan anggaran, pergeseran dan tambahan anggaran, EWS, dashboard, laporan, dan layanan API.
>
> • **Adaptor Anggaran di Odoo 10** (nama teknis usulan: ka_pkat_connector): pemanggil API dari titik transaksi SPM/SPPJ, PO, bon barang/jasa, Berita Acara/NTB, kas/bank, memo, dan pengirim jurnal; menggantikan ka_stock_account_pkrat.
>
> • **Migrasi data** PKAT dan Nomor Investasi carry over dari ka_logistik_pkrat (Odoo 10) ke Odoo 20.

Di luar lingkup: pemindahan modul transaksi (SPM, pengadaan, persediaan, akuntansi) ke Odoo 20, dan perubahan alur bisnis modul tersebut selain titik pemeriksaan anggaran.

### 1.3 Referensi

> • BRD Penambahan dan Perbaikan Pengendalian & Monitoring Anggaran versi 1.0, 21 Oktober 2026.
>
> • Project Charter Nomor P001-26-PC-001.
>
> • Pedoman Wewenang Pelaksanaan Penggunaan Anggaran Tahunan (berlaku sepanjang tidak bertentangan dengan hasil rapat; lihat BRD Lampiran C).
>
> • Kode program Odoo 10: ka_logistik_pkrat, ka_stock_account_pkrat, ka_logistik_spm, ka_spk, ka_purchase, ka_account, ka_stock_account, ka_base.
>
> • Contoh laporan Realisasi Anggaran PG Kebon Agung per Oktober 2026 (2BOAJZ).

### 1.4 Definisi dan Singkatan

| **Istilah**                      | **Keterangan**                                                                                                                      |
|----------------------------------|-------------------------------------------------------------------------------------------------------------------------------------|
| **Anggaran berlaku**             | Anggaran awal PKAT + pergeseran masuk − pergeseran keluar + tambahan yang disetujui                                                 |
| **Serapan**                      | Nilai PO terbit (tanpa PPN), dicatat per baris PO pada buku serapan                                                                 |
| **Realisasi**                    | Nilai jurnal posted Odoo 10, dicatat per baris jurnal pada buku realisasi                                                           |
| **Sisa Serapan / Sisa Anggaran** | Anggaran − Serapan / Anggaran − Realisasi                                                                                           |
| **Potensi serapan**              | Serapan + nilai SPM/SPPJ (HPS × kuantum) yang masih diproses                                                                        |
| **Kantung**                      | Kelompok anggaran yang menjadi batas penguncian; tingkat perkiraan, stasiun, atau bagian (bawaan bagian), dipisah upah dan non-upah |
| **Dasar penguncian**             | Pembanding batas: yearly (tahunan), ytd (s.d. bulan dokumen), atau mtd (bulan dokumen)                                              |
| **Nomor Investasi / proyek**     | Proyek investasi: Investasi Baru, PLB, Inventaris, Penggantian                                                                      |
| **Adaptor**                      | Modul Odoo 10 pemanggil API Odoo 20                                                                                                 |
| **Kunci idempotensi**            | Kode unik per operasi dokumen agar pengiriman ulang tidak tercatat ganda                                                            |
| **Fail-closed**                  | Bila Odoo 20 tidak terjangkau, PO dan transaksi realisasi ditolak                                                                   |
| **SIT / UAT**                    | System Integration Test / User Acceptance Test                                                                                      |

### 1.5 Konvensi

> • ID spesifikasi: **FS** (fungsional), **DM** (model data), **API** (layanan), **AD** (adaptor Odoo 10), **UI** (antarmuka), **AK** (hak akses), **NF** (non-fungsional), **MG** (migrasi), **TS** (pengujian).
>
> • Nama model, field, dan endpoint adalah usulan desain; boleh disesuaikan saat pengembangan selama perilaku pada dokumen ini terpenuhi.
>
> • Nilai uang dalam rupiah, dibulatkan 2 desimal. Tanggal memakai zona waktu WIB.

## 2. Deskripsi Umum Sistem

### 2.1 Arsitektur

_(gambar: lihat berkas Word)_

*Gambar 1. Arsitektur: Odoo 20 pusat anggaran, Odoo 10 tetap memproses transaksi*

| **Komponen**                         | **Tanggung jawab**                                                                                                | **Teknologi**                                  |
|--------------------------------------|-------------------------------------------------------------------------------------------------------------------|------------------------------------------------|
| **ka_pkat (Odoo 20)**                | Sumber kebenaran anggaran; menghitung dan memutuskan; menyimpan buku serapan/realisasi; layar, dashboard, laporan | Odoo 20, PostgreSQL, multi-company             |
| **API Anggaran (Odoo 20)**           | Layanan HTTPS/JSON untuk adaptor                                                                                  | Controller Odoo, autentikasi token             |
| **ka_pkat_connector (Odoo 10)**      | Hook pada tombol/metode transaksi; klien API; antrean kirim jurnal; cache referensi anggaran                      | Odoo 10, Python 2.7, pustaka requests          |
| **ka_logistik_pkrat (Odoo 10)**      | Menjadi cermin baca-saja untuk rujukan perkiraan PKAT dan Nomor Investasi pada dokumen Odoo 10                    | Tetap terpasang; isi disinkronkan dari Odoo 20 |
| **ka_stock_account_pkrat (Odoo 10)** | Dinonaktifkan                                                                                                     | Diganti adaptor                                |

### 2.2 Prinsip Desain

> • **Satu pengambil keputusan.** Semua keputusan lewat/peringatan/tolak dihitung di Odoo 20; adaptor hanya meneruskan data dan menampilkan hasil.
>
> • **Atomik.** Pemeriksaan dan pencatatan serapan PO terjadi dalam satu transaksi basis data dengan penguncian baris kantung.
>
> • **Idempoten.** Setiap operasi dokumen membawa kunci unik; pengiriman ulang mengembalikan hasil yang sama.
>
> • **Kode, bukan id.** Pertukaran data memakai kode company, perkiraan, stasiun, bagian, Nomor Investasi, dan nomor dokumen.
>
> • **Tanggal dokumen.** Tahun dan bulan anggaran ditentukan dari tanggal dokumen, bukan tanggal sistem.
>
> • **Tanpa bypass.** Tidak ada unlock manual; kunci terbuka hanya bila anggaran bertambah lewat pergeseran/tambahan yang disetujui.
>
> • **Konfigurasi, bukan kode.** Tingkat kantung, dasar penguncian, dan ambang EWS diatur Bagian Anggaran Kantor Direksi.

### 2.3 Pengguna dan Grup

| **Grup Odoo 20**     | **Pengguna**                   | **Hak utama**                                                             |
|----------------------|--------------------------------|---------------------------------------------------------------------------|
| **pkat_anggaran_kd** | Bagian Anggaran Kantor Direksi | Kelola semua data anggaran dan konfigurasi; proses tambahan; kunci manual |
| **pkat_tuk_unit**    | TUK Unit                       | Siapkan rekap PKAT; ajukan pergeseran/tambahan; lihat unit                |
| **pkat_pemimpin**    | Pemimpin Pabrik / Kadiv        | Setujui pergeseran/tambahan unit; lihat unit                              |
| **pkat_pengguna**    | Kasubsi, Kasi, Kabag           | Lihat anggaran sesuai area (stasiun/seksi/bagian)                         |
| **pkat_direksi**     | Direksi                        | Lihat semua unit                                                          |
| **pkat_auditor**     | Auditor / SPI                  | Baca saja semua data dan log                                              |
| **pkat_admin**       | PDE                            | Konfigurasi teknis, token API, pemantauan sinkronisasi                    |
| **pkat_api**         | Pengguna teknis per company    | Hanya akses layanan API                                                   |

### 2.4 Lingkungan Operasi dan Ketergantungan

> • Odoo 20 multi-company: Kantor Direksi, PG Kebon Agung, PG Trangkil; dapat diakses dari ketiga unit.
>
> • Odoo 10 tiap company dapat menjangkau Odoo 20 melalui HTTPS; target latensi jaringan \< 300 ms.
>
> • Semua pengguna pada 2.3 memiliki akun Odoo 20; login Odoo 10 dan Odoo 20 dipadankan lewat login atau NIK pegawai.
>
> • Odoo 10 tetap menjadi buku besar resmi.

## 3. Model Data (Odoo 20)

_(gambar: lihat berkas Word)_

*Gambar 2. Hubungan antar model utama*

Seluruh model anggaran memiliki company_id dan tahun anggaran bertipe angka, dengan record rule per company (BRD PK-09, NF-04). Field audit bawaan Odoo (create/write uid dan date) berlaku untuk semua model.

### 3.1 Konfigurasi

**DM-01 pkat.config (satu per company dan tahun anggaran)**

| **Field**               | **Tipe**     | **Keterangan**                                                 |
|-------------------------|--------------|----------------------------------------------------------------|
| **company_id, year**    | m2o, integer | Kunci unik                                                     |
| **pocket_level**        | selection    | account / cost_center / department; bawaan department (bagian) |
| **lock_basis**          | selection    | yearly / ytd / mtd; bawaan yearly                              |
| **ews_yellow, ews_red** | float        | Ambang %; bawaan 75 dan 100                                    |
| **sync_stale_minutes**  | integer      | Batas peringatan sinkronisasi jurnal; bawaan 60                |
| **lock_active**         | boolean      | Penguncian aktif; bawaan aktif                                 |

*Perubahan pocket_level atau lock_basis hanya oleh grup pkat_anggaran_kd, tercatat di riwayat, dan memicu hitung ulang kantung.*

### 3.2 Master

**DM-02 pkat.department, pkat.cost.center, pkat.account**

| **Field**                                                   | **Tipe**  | **Keterangan**                                                  |
|-------------------------------------------------------------|-----------|-----------------------------------------------------------------|
| **pkat.department: code, name, parent_id, manager_user_id** | char, m2o | Bagian/seksi/sub seksi; padanan hr.department Odoo 10           |
| **pkat.cost.center: code, name, department_id, section_id** | char, m2o | Stasiun; padanan ka_account.stasiun; kode = digit 3–4 perkiraan |
| **pkat.account: code, name**                                | char      | Nomor perkiraan 8 digit; padanan account.account                |
| **pkat.account: cost_center_id, department_id**             | m2o       | Stasiun dan bagian pemilik perkiraan                            |
| **pkat.account: cost_item**                                 | char(2)   | Jenis biaya = digit 7–8                                         |
| **pkat.account: wage_type**                                 | selection | upah / non_upah (dari field upah perkiraan Odoo 10)             |
| **pkat.account: kind**                                      | selection | expense / income / investment                                   |
| **pkat.account: unit_pocket**                               | selection | tenaga_kerja / barang_jasa / bahan_baku_tebu                    |
| **pkat.account: is_spt**                                    | boolean   | Anggaran Tebu SPT: tidak dikunci, tidak ikut pergeseran         |
| **pkat.account: active**                                    | boolean   |                                                                 |

### 3.3 Anggaran Biaya dan Pendapatan

**DM-03 pkat.budget (PKAT per stasiun per tahun)**

| **Field**                | **Tipe**     | **Keterangan**                                                          |
|--------------------------|--------------|-------------------------------------------------------------------------|
| **cost_center_id, year** | m2o, integer | Unik per company                                                        |
| **state**                | selection    | draft, proses, pengajuan, penyesuaian, proses_direksi, approved, cancel |
| **line_ids**             | o2m          | pkat.budget.line                                                        |

**DM-04 pkat.budget.line (anggaran per perkiraan)**

| **Field**                                                      | **Tipe**         | **Keterangan**                                             |
|----------------------------------------------------------------|------------------|------------------------------------------------------------|
| **budget_id, account_id**                                      | m2o              | Unik per budget                                            |
| **amount_goods, amount_nongoods, amount_wage, amount_project** | monetary         | Komponen barang, non-barang, tenaga kerja, proyek          |
| **amount_initial**                                             | monetary         | Anggaran awal = jumlah komponen; terkunci setelah approved |
| **shift_in, shift_out, amount_added**                          | monetary         | Dihitung dari permohonan berstatus diproses                |
| **amount_current**                                             | monetary         | Anggaran berlaku                                           |
| **commitment, realization**                                    | monetary         | Agregat buku serapan dan realisasi tahun berjalan          |
| **remain_commitment, remain_budget**                           | monetary         | Sisa Serapan, Sisa Anggaran                                |
| **pct_commitment, pct_realization, ews_color**                 | float, selection | green / yellow / red                                       |
| **month_ids**                                                  | o2m              | 12 baris pkat.budget.month                                 |

**DM-05 pkat.budget.month**

| **Field**                   | **Tipe**          | **Keterangan**                                   |
|-----------------------------|-------------------|--------------------------------------------------|
| **line_id, month**          | m2o, integer 1–12 |                                                  |
| **amount_plan**             | monetary          | Rencana bulan; Σ 12 bulan wajib = amount_current |
| **commitment, realization** | monetary          | Agregat bulan                                    |

### 3.4 Anggaran Investasi

**DM-06 pkat.project (Nomor Investasi)**

| **Field**                                 | **Tipe**        | **Keterangan**                                                              |
|-------------------------------------------|-----------------|-----------------------------------------------------------------------------|
| **code, name, specification**             | char, text      | Nomor dan nama proyek                                                       |
| **project_type**                          | selection       | investasi_baru / plb / inventaris / penggantian / memorandum / rutin        |
| **cost_center_id, department_id**         | m2o             |                                                                             |
| **expense_account_id**                    | m2o             | Khusus PLB: perkiraan biaya rutin yang dibebani                             |
| **amount_total**                          | monetary        | Nilai proyek (PKAT)                                                         |
| **year_ids**                              | o2m             | pkat.project.year: tahun, alokasi, tambahan, carry over, 12 rencana bulanan |
| **commitment, realization, physical_pct** | monetary, float | Serapan PO, realisasi keuangan, realisasi fisik (input manual)              |
| **state**                                 | selection       | draft, pengajuan, approved, closed, cancel                                  |
| **closed_date**                           | date            | Proyek ditutup tidak menerima transaksi baru                                |

### 3.5 Kantung

**DM-07 pkat.pocket**

| **Field**                                                   | **Tipe**                | **Keterangan**                                          |
|-------------------------------------------------------------|-------------------------|---------------------------------------------------------|
| **company_id, year, level**                                 | m2o, integer, selection | Level mengikuti pkat.config                             |
| **ref_account_id / ref_cost_center_id / ref_department_id** | m2o                     | Satu terisi sesuai level                                |
| **wage_type**                                               | selection               | upah / non_upah                                         |
| **amount_current, commitment, realization**                 | monetary                | Agregat dari pkat.budget.line anggotanya (tanpa is_spt) |
| **locked_po, locked_real**                                  | boolean                 | Terhitung: terpakai ≥ batas menurut dasar penguncian    |
| **manual_lock, manual_lock_reason**                         | boolean, text           | Kunci manual Bagian Anggaran                            |

*Kantung disimpan sebagai tabel agar dapat dikunci barisnya (SELECT … FOR UPDATE) saat pemeriksaan; nilainya diperbarui dalam transaksi yang sama dengan buku serapan/realisasi.*

### 3.6 Buku Transaksi

**DM-08 pkat.commitment (buku serapan)**

| **Field**                                         | **Tipe**   | **Keterangan**                                 |
|---------------------------------------------------|------------|------------------------------------------------|
| **idem_key**                                      | char, unik | Kunci idempotensi baris PO                     |
| **po_number, po_line_ref, po_date, partner_name** | char, date | Rujukan dokumen Odoo 10                        |
| **po_kind**                                       | selection  | rutin / plb / investasi                        |
| **account_id, project_id**                        | m2o        | Perkiraan dan/atau Nomor Investasi             |
| **amount**                                        | monetary   | Nilai baris tanpa PPN, dalam rupiah            |
| **state**                                         | selection  | active / cancelled                             |
| **mirror_of_id**                                  | m2o        | Baris cermin PO PLB pada perkiraan biaya rutin |

**DM-09 pkat.realization (buku realisasi)**

| **Field**                                       | **Tipe**                  | **Keterangan**                                                        |
|-------------------------------------------------|---------------------------|-----------------------------------------------------------------------|
| **src_move_line_id**                            | integer, unik per company | Id baris jurnal Odoo 10                                               |
| **move_name, date, source_type, source_number** | char, date, selection     | Sumber: bon, ba_ntb, kas_bank, memo, lainnya                          |
| **account_id, project_id**                      | m2o                       | Perkiraan; proyek dari analytic Nomor Investasi                       |
| **debit, credit, is_correction**                | monetary, boolean         | is_correction dari tanda Kor. jurnal Odoo 10                          |
| **amount_counted**                              | monetary                  | Biaya: debit − kredit. Proyek: debit; kredit hanya bila is_correction |
| **state**                                       | selection                 | posted / reversed                                                     |

**DM-10 pkat.potential (SPM/SPPJ dalam proses)**

| **Field**                                | **Tipe**              | **Keterangan**                          |
|------------------------------------------|-----------------------|-----------------------------------------|
| **idem_key, doc_number, doc_type, date** | char, selection, date | Baris SPM/SPPJ                          |
| **account_id, project_id, amount**       | m2o, monetary         | HPS × kuantum                           |
| **state**                                | selection             | open / converted (sudah PO) / cancelled |
| **over_budget, reason**                  | boolean, text         | Peringatan dan alasan permintaan        |

### 3.7 Permohonan Pergeseran dan Tambahan

**DM-11 pkat.change.request dan pkat.change.request.line**

| **Field**                                        | **Tipe**           | **Keterangan**                                                   |
|--------------------------------------------------|--------------------|------------------------------------------------------------------|
| **name, date, company_id, year**                 | char, date         | Nomor otomatis                                                   |
| **requester_id**                                 | m2o                | TUK unit                                                         |
| **state**                                        | selection          | draft, submitted, approved_unit, waiting_kd, processed, rejected |
| **has_addition**                                 | boolean            | Terhitung: ada baris jenis T                                     |
| **letter_number, letter_date, attachment**       | char, date, binary | Surat persetujuan Direksi / Dewan Komisaris / Pemegang Saham     |
| **line: kind**                                   | selection          | G (pergeseran), T (tambahan), J (geser jadwal bulan)             |
| **line: receiver_line_id / receiver_project_id** | m2o                | Pos penerima                                                     |
| **line: giver_line_id**                          | m2o                | Pos pemberi (wajib untuk G)                                      |
| **line: month_from, month_to**                   | integer            | Untuk J; opsional untuk G                                        |
| **line: amount, reason, benefit_risk**           | monetary, text     |                                                                  |
| **line: pct_of_budget, approval_tier**           | float, selection   | Untuk tambahan investasi: direksi / dekom / pemegang_saham       |

### 3.8 Log

| **Model**                | **Isi**                                                                                                                                      |
|--------------------------|----------------------------------------------------------------------------------------------------------------------------------------------|
| **DM-12 pkat.check.log** | Setiap peringatan dan penolakan: waktu, pengguna, company, jenis cek, dokumen, perkiraan/proyek, kantung, batas, terpakai, nilai, kode hasil |
| **DM-13 pkat.lock.log**  | Perubahan status kunci kantung (otomatis/manual), alasan, pengguna                                                                           |
| **DM-14 pkat.api.log**   | Setiap panggilan API: endpoint, kunci idempotensi, kode hasil, durasi, alamat asal                                                           |
| **DM-15 pkat.reconcile** | Hasil rekonsiliasi harian per perkiraan/bulan: total Odoo 10, total Odoo 20, selisih, status tindak lanjut                                   |

## 4. Spesifikasi Fungsional

### 4.1 Data Anggaran PKAT

| **ID**       | **Spesifikasi**                                                                                                                                                                                                                                                 | **Ref. BRD**        |
|--------------|-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|---------------------|
| **FS-PK-01** | Impor PKAT dari Excel berformat baku (template dapat diunduh). Kolom: tahun, kode stasiun, nomor perkiraan, komponen (barang, non-barang, tenaga kerja, proyek), rencana Januari–Desember. Hanya grup pkat_anggaran_kd.                                         | PK-04               |
| **FS-PK-02** | Validasi impor per baris: perkiraan dan stasiun terdaftar dan aktif; perkiraan milik stasiun tersebut; tidak duplikat; nilai ≥ 0; Σ bulanan = Σ komponen. Baris gagal ditampilkan dengan alasan dan dapat diunduh; impor bersifat semua-atau-tidak per stasiun. | PK-03, PK-04        |
| **FS-PK-03** | Alur status pkat.budget: draft → proses → pengajuan → penyesuaian → proses_direksi → approved; cancel dari status mana pun sebelum approved. Hanya budget approved yang dipakai pemeriksaan dan layanan Daftar anggaran.                                        | PK-05               |
| **FS-PK-04** | Setelah approved, amount_initial dan komponen tidak dapat diedit oleh siapa pun; perubahan hanya dari permohonan berstatus processed.                                                                                                                           | PK-06, PK-08        |
| **FS-PK-05** | Rencana pendapatan diimpor dan dimonitor; perkiraan kind = income tidak pernah diperiksa atau dikunci.                                                                                                                                                          | PK-10               |
| **FS-PK-06** | Peringatan (bukan galat) bila total bulanan ≠ total tahunan saat edit draft; pengajuan ditolak sampai sama.                                                                                                                                                     | PK-03               |
| **FS-PK-07** | Proyek investasi diimpor/diinput per Nomor Investasi dengan alokasi per tahun dan rencana bulanan. Proyek bertipe PLB hanya satu tahun.                                                                                                                         | PK-07, PK-14, IV-01 |
| **FS-PK-08** | Proses tutup tahun investasi: sisa (alokasi − realisasi) proyek berstatus approved disalin sebagai carry over ke tahun berikutnya oleh Bagian Anggaran.                                                                                                         | PK-07               |
| **FS-PK-09** | Master perkiraan, stasiun, dan bagian diterima dari Odoo 10 (API-08); perkiraan baru tanpa stasiun/bagian ditandai untuk dilengkapi Bagian Anggaran sebelum dapat dianggarkan.                                                                                  | PK-11, IN-09        |

### 4.2 Serapan, Realisasi, dan Sisa

| **ID**       | **Spesifikasi**                                                                                                                                                                                                       | **Ref. BRD**        |
|--------------|-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|---------------------|
| **FS-SR-01** | Serapan perkiraan = Σ pkat.commitment.amount berstatus active pada tahun tanggal PO. Serapan proyek = Σ baris dengan project_id tersebut.                                                                             | SR-02, BR-02        |
| **FS-SR-02** | Nilai baris PO = subtotal tanpa PPN. PO valas dikonversi ke rupiah dengan kurs tanggal PO yang dikirim adaptor.                                                                                                       | SR-02               |
| **FS-SR-03** | PO dibatalkan: seluruh baris serapannya menjadi cancelled dan agregat berkurang. Tidak ada pengurangan untuk penerimaan sebagian.                                                                                     | SR-03               |
| **FS-SR-04** | PO PLB (po_kind = plb): dibuat dua baris serapan, satu pada Nomor PLB dan satu cermin pada expense_account_id proyek; keduanya dibatalkan bersama.                                                                    | SR-09               |
| **FS-SR-05** | PO konsinyasi diperlakukan sama dengan PO lain.                                                                                                                                                                       | SR-08               |
| **FS-SR-06** | Realisasi perkiraan biaya = Σ amount_counted baris posted pada tahun tanggal jurnal. Realisasi proyek = Σ debit baris akun 299x dan akun aset ber-analytic Nomor Investasi; kredit hanya dihitung bila is_correction. | SR-04, IV-02, BR-03 |
| **FS-SR-07** | Jurnal di-unpost atau dihapus di Odoo 10: baris realisasi menjadi reversed dan agregat berkurang.                                                                                                                     | SR-05               |
| **FS-SR-08** | Agregat pada budget.line, budget.month, project, dan pocket diperbarui dalam transaksi yang sama dengan penulisan buku; tidak bergantung pada cron.                                                                   | SR-05, SR-06        |
| **FS-SR-09** | Setiap angka serapan/realisasi dapat dibuka menjadi daftar baris buku berisi nomor dokumen Odoo 10.                                                                                                                   | SR-07               |

### 4.3 Mesin Pemeriksaan Anggaran

_(gambar: lihat berkas Word)_

*Gambar 3. Alur pemeriksaan anggaran*

<table>
<colgroup>
<col style="width: 12%" />
<col style="width: 71%" />
<col style="width: 16%" />
</colgroup>
<thead>
<tr class="header">
<th><strong>ID</strong></th>
<th><strong>Spesifikasi</strong></th>
<th><strong>Ref. BRD</strong></th>
</tr>
</thead>
<tbody>
<tr class="odd">
<td><strong>FS-CK-01</strong></td>
<td>Tiga jenis cek: SPM (permintaan), PO (serapan), REALISASI (bon barang/jasa, BA/NTB, kas/bank, memo). Masukan berupa satu dokumen dengan satu atau lebih baris.</td>
<td>BR-07</td>
</tr>
<tr class="even">
<td><strong>FS-CK-02</strong></td>
<td>Baris dilewati tanpa cek bila perkiraan bukan biaya/investasi, is_spt, atau lock_active mati. Perkiraan pendapatan dan neraca selain akun proyek tidak dicek.</td>
<td>PK-10, PR-14</td>
</tr>
<tr class="odd">
<td><strong>FS-CK-03</strong></td>
<td>Baris biaya tanpa pkat.budget.line approved pada tahun dokumen → REJECT_NO_BUDGET untuk PO dan REALISASI; untuk SPM juga ditolak.</td>
<td>PR-11, PP-02</td>
</tr>
<tr class="even">
<td><strong>FS-CK-04</strong></td>
<td>Penentuan kantung baris: sesuai pocket_level (perkiraan itu sendiri, stasiun, atau bagian perkiraan) dan wage_type perkiraan.</td>
<td>LK-01, BR-08</td>
</tr>
<tr class="odd">
<td><strong>FS-CK-05</strong></td>
<td><p>Batas dan terpakai menurut lock_basis, dengan M = bulan tanggal dokumen:</p>
<p>- yearly: batas = anggaran berlaku setahun; terpakai = kumulatif setahun;</p>
<p>- ytd: batas = Σ rencana bulan 1 s.d. M; terpakai = kumulatif s.d. akhir bulan M;</p>
<p>- mtd: batas = rencana bulan M; terpakai = dalam bulan M.</p></td>
<td>PR-12, BR-12</td>
</tr>
<tr class="even">
<td><strong>FS-CK-06</strong></td>
<td>Terpakai = serapan (cek SPM dan PO) atau realisasi (cek REALISASI). Untuk SPM ditambah potensi baris lain dalam pengajuan yang sama.</td>
<td>BR-05, BR-07</td>
</tr>
<tr class="odd">
<td><strong>FS-CK-07</strong></td>
<td>Keputusan kantung: terpakai + nilai &gt; batas → SPM: WARN_POCKET_OVER; PO dan REALISASI: REJECT_POCKET_OVER. Sama dengan batas (tepat 100%) diperbolehkan.</td>
<td>PP-04, PR-02, PR-03</td>
</tr>
<tr class="even">
<td><strong>FS-CK-08</strong></td>
<td>Bila kantung lolos tetapi perkiraan itu sendiri melebihi anggarannya → WARN_ACCOUNT_OVER; transaksi tetap dapat diproses.</td>
<td>PR-04</td>
</tr>
<tr class="odd">
<td><strong>FS-CK-09</strong></td>
<td>Baris ber-Nomor Investasi: terpakai proyek + nilai &gt; alokasi berlaku proyek → SPM: peringatan; PO dan REALISASI: REJECT_PROJECT_OVER. Proyek closed → REJECT_PROJECT_CLOSED. PO PLB dicek pada proyek dan pada kantung perkiraan biaya rutin.</td>
<td>PR-05, IV-03</td>
</tr>
<tr class="even">
<td><strong>FS-CK-10</strong></td>
<td>Kantung dengan manual_lock → REJECT_MANUAL_LOCK untuk PO dan REALISASI.</td>
<td>LK-04</td>
</tr>
<tr class="odd">
<td><strong>FS-CK-11</strong></td>
<td>Beberapa baris dalam satu dokumen dihitung berurutan dan kumulatif per kantung. Satu baris ditolak → seluruh dokumen ditolak dan tidak ada serapan yang dicatat.</td>
<td>PR-06</td>
</tr>
<tr class="even">
<td><strong>FS-CK-12</strong></td>
<td>Cek PO dan pencatatan serapan dilakukan dalam satu transaksi dengan mengunci baris pkat.pocket / pkat.project terkait, diurutkan menurut id untuk mencegah deadlock.</td>
<td>PR-06, NF-03</td>
</tr>
<tr class="odd">
<td><strong>FS-CK-13</strong></td>
<td>Setiap hasil WARN dan REJECT ditulis ke pkat.check.log. Pesan memuat perkiraan, kantung, batas, terpakai, nilai, kekurangan, dan langkah lanjut (ajukan pergeseran/tambahan melalui TUK unit).</td>
<td>PR-07, PR-10</td>
</tr>
<tr class="even">
<td><strong>FS-CK-14</strong></td>
<td>Respons selalu memuat posisi anggaran perkiraan dan kantung (anggaran, serapan, realisasi, sisa serapan, sisa anggaran, %, warna EWS).</td>
<td>PP-03, EW-03</td>
</tr>
</tbody>
</table>

### 4.4 Penguncian Kantung

| **ID**       | **Spesifikasi**                                                                                                                                                                                                                       | **Ref. BRD** |
|--------------|---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|--------------|
| **FS-LK-01** | locked_po bernilai benar bila serapan ≥ batas; locked_real bila realisasi ≥ batas, menurut dasar penguncian pada bulan berjalan. Perubahan nilai dicatat di pkat.lock.log dan dinotifikasi ke TUK unit dan pengguna anggaran terkait. | LK-02        |
| **FS-LK-02** | Tidak tersedia tombol atau layanan untuk membuka kunci otomatis. Kunci terbuka sendiri saat batas bertambah (permohonan processed) atau terpakai berkurang (PO batal, jurnal dibalik).                                                | LK-03, PR-13 |
| **FS-LK-03** | Kunci manual: Bagian Anggaran dapat menyalakan/mematikan manual_lock dengan alasan wajib; tercatat di log.                                                                                                                            | LK-04        |
| **FS-LK-04** | Peringatan dini: saat % serapan atau % realisasi kantung melewati ews_yellow, notifikasi dikirim ke TUK unit agar pergeseran/tambahan diajukan sebelum terkunci.                                                                      | LK-05, EW-04 |

### 4.5 Pergeseran Anggaran

| **ID**       | **Spesifikasi**                                                                                                                                                                                                                                                                                                                                  | **Ref. BRD** |
|--------------|--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|--------------|
| **FS-SW-01** | Satu permohonan memuat banyak baris berjenis G, T, atau J sesuai formulir Pedoman. Hanya grup pkat_tuk_unit yang membuat dan mengajukan.                                                                                                                                                                                                         | SW-01        |
| **FS-SW-02** | Validasi baris G: nilai ≤ sisa pos pemberi = anggaran berlaku − maks(realisasi, serapan); dihitung ulang saat persetujuan.                                                                                                                                                                                                                       | SW-02        |
| **FS-SW-03** | Validasi kesetaraan G: pemberi dan penerima dalam unit (company) yang sama; salah satu: stasiun sama, bagian sama, atau antar bagian dalam unit.                                                                                                                                                                                                 | SW-03        |
| **FS-SW-04** | Perkiraan jenis biaya 00 dan 01 hanya ke perkiraan dengan jenis biaya yang sama. Baris yang menyentuh wage_type = upah mewajibkan centang "sudah dikoordinasikan dengan Divisi SDM & Umum" dan catatan.                                                                                                                                          | SW-04        |
| **FS-SW-05** | Antar bagian: hanya non_upah ↔ non_upah, atau di dalam unit_pocket bahan_baku_tebu. Perkiraan is_spt tidak dapat menjadi pemberi maupun penerima. Tidak ada pergeseran biaya ↔ investasi.                                                                                                                                                        | SW-05        |
| **FS-SW-06** | Alur permohonan tanpa baris T: draft → submitted → (Pemimpin Pabrik menyetujui) → processed otomatis. Saat processed: shift_out pemberi dan shift_in penerima bertambah, rencana bulanan disesuaikan (bawaan: bulan berjalan s.d. Desember secara proporsional, atau bulan yang dipilih), kantung dihitung ulang, notifikasi ke Bagian Anggaran. | SW-06, SW-08 |
| **FS-SW-07** | Baris J memindahkan rencana antar bulan pada perkiraan yang sama; total tahunan tidak berubah; alur sama dengan FS-SW-06.                                                                                                                                                                                                                        | SW-07        |
| **FS-SW-08** | Penolakan mewajibkan alasan; permohonan rejected tidak mengubah anggaran. Seluruh perubahan status tercatat di chatter.                                                                                                                                                                                                                          | SW-08        |

### 4.6 Tambahan Anggaran

| **ID**       | **Spesifikasi**                                                                                                                                                                                                                                                    | **Ref. BRD**        |
|--------------|--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|---------------------|
| **FS-TA-01** | Permohonan dengan baris T: draft → submitted → approved_unit (Pemimpin Pabrik) → waiting_kd → processed (Bagian Anggaran) atau rejected.                                                                                                                           | TA-01               |
| **FS-TA-02** | Perpindahan waiting_kd → processed mewajibkan nomor dan tanggal surat persetujuan Direksi beserta lampiran; pengajuan ke Direksi dilakukan di luar sistem.                                                                                                         | TA-01, TA-03        |
| **FS-TA-03** | Tambahan investasi/PLB: sistem menghitung % kumulatif tambahan terhadap PKAT awal Nomor Investasi dan menetapkan approval_tier: ≤ 5% direksi; \> 5% s.d. 10% dekom; \> 10% pemegang_saham. Untuk dekom/pemegang_saham, data surat pihak tersebut juga wajib diisi. | TA-02, TA-04, BR-09 |
| **FS-TA-04** | Investasi mendesak tanpa anggaran: baris T dengan Nomor Investasi baru berstatus draft; tier pemegang_saham; proyek menjadi approved saat permohonan processed.                                                                                                    | TA-02               |
| **FS-TA-05** | Saat processed: amount_added penerima bertambah, rencana bulanan disesuaikan seperti FS-SW-06, kantung dihitung ulang.                                                                                                                                             | TA-06               |

### 4.7 Proyek Investasi

| **ID**       | **Spesifikasi**                                                                                                                                             | **Ref. BRD** |
|--------------|-------------------------------------------------------------------------------------------------------------------------------------------------------------|--------------|
| **FS-IV-01** | Penutupan proyek/PLB oleh Bagian Anggaran: state = closed, closed_date terisi; cek berikutnya ditolak (REJECT_PROJECT_CLOSED).                              | IV-03        |
| **FS-IV-02** | Pemindahan saldo PLB ke biaya dilakukan dengan jurnal di Odoo 10; realisasinya masuk ke perkiraan biaya melalui buku realisasi dan ikut dicek seperti memo. | IV-03        |
| **FS-IV-03** | Realisasi fisik (%) diinput manual per proyek dengan tanggal dan catatan; riwayat disimpan.                                                                 | IV-04, BR-03 |
| **FS-IV-04** | Layar proyek menampilkan anggaran, serapan, realisasi, sisa serapan, sisa anggaran, realisasi fisik, dan status, per tahun dan per bulan.                   | IV-04, PK-14 |

### 4.8 EWS dan Notifikasi

| **ID**       | **Spesifikasi**                                                                                                                                                                           | **Ref. BRD** |
|--------------|-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|--------------|
| **FS-EW-01** | Warna dihitung dari %: hijau ≤ ews_yellow; kuning \> ews_yellow s.d. ews_red; merah \> ews_red. Dihitung terpisah untuk serapan dan realisasi, pada perkiraan, kantung, unit, dan proyek. | EW-01, EW-02 |
| **FS-EW-02** | Pada cek SPM, warna yang dikembalikan memakai % potensi serapan.                                                                                                                          | BR-06        |
| **FS-EW-03** | Notifikasi Odoo (activity/email) saat kantung berpindah ke kuning, merah, atau terkunci; penerima: TUK unit, pengguna anggaran kantung, atasannya. Integrasi WhatsApp bersifat opsional.  | EW-04        |

## 5. Spesifikasi API Anggaran

### 5.1 Ketentuan Umum

| **ID**       | **Spesifikasi**                                                                                                                                                                 | **Ref. BRD** |
|--------------|---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|--------------|
| **API-G-01** | Protokol HTTPS, metode POST, isi JSON (UTF-8). Alamat dasar: /api/pkat/v1/.                                                                                                     | NF-05        |
| **API-G-02** | Header wajib: X-PKAT-Token (token per company), X-PKAT-Company (kode company), X-PKAT-User (login pengguna Odoo 10), X-Idempotency-Key untuk layanan yang mengubah data.        | IN-05, IN-10 |
| **API-G-03** | Token disimpan ter-hash di Odoo 20; dapat diganti dan dicabut oleh pkat_admin; tidak ada nilai bawaan. Token salah → HTTP 401 tanpa rincian.                                    | NF-05        |
| **API-G-04** | Endpoint hanya layanan pada 5.2; tidak ada layanan generik untuk memanggil model atau method.                                                                                   | NF-05        |
| **API-G-05** | Kunci idempotensi: company:model:id_dokumen:operasi:versi. Kunci yang sudah pernah diproses mengembalikan respons tersimpan tanpa memproses ulang.                              | IN-02        |
| **API-G-06** | Amplop respons: status (ok / warn / reject / error), code, message (bahasa Indonesia, siap tampil), data. Kode HTTP 200 untuk ok/warn/reject; 4xx/5xx hanya untuk galat teknis. | PR-07        |
| **API-G-07** | Batas waktu klien 5 detik untuk cek, 30 detik untuk kirim massal. Target waktu proses server \< 1 detik per dokumen.                                                            | NF-02        |
| **API-G-08** | Setiap panggilan dicatat di pkat.api.log.                                                                                                                                       | IN-05, NF-06 |

**Kode hasil**

| **Kode**                  | **Status** | **Arti**                                                             |
|---------------------------|------------|----------------------------------------------------------------------|
| **OK**                    | ok         | Lolos                                                                |
| **PASS_UNCONTROLLED**     | ok         | Perkiraan tidak dikendalikan (pendapatan, Tebu SPT, penguncian mati) |
| **WARN_ACCOUNT_OVER**     | warn       | Perkiraan melebihi anggaran, kantung masih cukup                     |
| **WARN_POCKET_OVER**      | warn       | SPM/SPPJ: potensi serapan melebihi kantung atau proyek               |
| **REJECT_NO_BUDGET**      | reject     | Perkiraan tidak dianggarkan                                          |
| **REJECT_POCKET_OVER**    | reject     | Serapan atau realisasi kantung akan melebihi batas                   |
| **REJECT_PROJECT_OVER**   | reject     | Nomor Investasi akan melebihi anggaran                               |
| **REJECT_PROJECT_CLOSED** | reject     | Proyek sudah ditutup                                                 |
| **REJECT_MANUAL_LOCK**    | reject     | Kantung dikunci manual oleh Bagian Anggaran                          |
| **ERR_VALIDATION**        | error      | Data tidak lengkap atau kode tidak dikenal                           |
| **ERR_ACCESS**            | error      | Pengguna tidak berhak atas data yang diminta                         |

### 5.2 Daftar Layanan

| **ID**     | **Endpoint**      | **Masukan utama**                                                                                                                             | **Keluaran / perilaku**                                                                                                         |
|------------|-------------------|-----------------------------------------------------------------------------------------------------------------------------------------------|---------------------------------------------------------------------------------------------------------------------------------|
| **API-01** | budget/list       | tahun, jenis investasi, Nomor Investasi, stasiun/bagian (opsional)                                                                            | Daftar anggaran berstatus Disetujui: perkiraan per stasiun dan Nomor Investasi (kode, nama, nilai); disaring hak akses pengguna |
| **API-02** | budget/info       | tahun, perkiraan atau Nomor Investasi, stasiun/bagian, tanggal (opsional), jenis kantung (bagian, stasiun, kasi, kasubsi, perkiraan)          | Anggaran, serapan, realisasi, sisa serapan, sisa anggaran, %, warna EWS, status kunci                                           |
| **API-03** | spm/check         | jenis (SPM/SPPJ), nomor, tanggal, baris: perkiraan/proyek, HPS, kuantum; simpan (ya/tidak)                                                    | Hasil per baris (OK/WARN/REJECT_NO_BUDGET) + posisi; bila simpan = ya, baris dicatat sebagai potensi                            |
| **API-04** | commitment/check  | nomor PO, tanggal, jenis PO, rekanan, kurs, baris: ref, perkiraan, proyek, subtotal tanpa PPN                                                 | Cek serapan + catat buku serapan secara atomik; menutup potensi SPM asal (converted)                                            |
| **API-05** | commitment/cancel | nomor PO                                                                                                                                      | Baris serapan PO menjadi cancelled; posisi baru                                                                                 |
| **API-06** | realization/check | jenis sumber, nomor, tanggal, baris: perkiraan, proyek, nilai                                                                                 | Lolos / peringatan / tolak; tidak mencatat apa pun selain log                                                                   |
| **API-07** | journal/push      | daftar baris jurnal: id, nama jurnal, tanggal, perkiraan, analytic, debit, kredit, Kor., sumber, operasi (post/unpost/delete); maks 500 baris | Jumlah diterima; baris ditolak beserta alasan                                                                                   |
| **API-08** | master/sync       | daftar perkiraan, stasiun, bagian (kode, nama, induk, jenis upah, aktif)                                                                      | Jumlah dibuat/diperbarui                                                                                                        |
| **API-09** | access/scope      | (dari header pengguna)                                                                                                                        | Daftar unit, bagian, stasiun yang boleh dilihat pengguna                                                                        |
| **API-10** | journal/reconcile | tahun, bulan, total debit−kredit per perkiraan dari Odoo 10                                                                                   | Selisih per perkiraan; tersimpan di pkat.reconcile                                                                              |
| **API-11** | ping              | –                                                                                                                                             | Status layanan dan waktu server                                                                                                 |

### 5.3 Contoh Pertukaran Data

**API-04 commitment/check: permintaan**

<table>
<colgroup>
<col style="width: 100%" />
</colgroup>
<thead>
<tr class="header">
<th><p>POST /api/pkat/v1/commitment/check</p>
<p>X-PKAT-Company: PGKBA X-PKAT-User: logistik01</p>
<p>X-Idempotency-Key: PGKBA:purchase.order:48211:confirm:1</p>
<p>{</p>
<p>"po_number": "SP/KBA/2027/00125", "po_date": "2027-03-14",</p>
<p>"po_kind": "rutin", "partner": "PT Contoh Rekanan",</p>
<p>"currency": "IDR", "rate": 1,</p>
<p>"lines": [</p>
<p>{"ref": "48211-1", "account": "50025259", "project": null, "amount": 20000000},</p>
<p>{"ref": "48211-2", "account": "50025240", "project": null, "amount": 5500000}</p>
<p>]</p>
<p>}</p></th>
</tr>
</thead>
<tbody>
</tbody>
</table>

**API-04 commitment/check: respons ditolak**

<table>
<colgroup>
<col style="width: 100%" />
</colgroup>
<thead>
<tr class="header">
<th><p>{</p>
<p>"status": "reject", "code": "REJECT_POCKET_OVER",</p>
<p>"message": "PO tidak dapat diproses. Serapan kantung Bagian Pabrikasi (non-upah)</p>
<p>akan menjadi 104,2% dari anggaran. Kekurangan Rp 3.150.000.</p>
<p>Ajukan pergeseran atau tambahan anggaran melalui TUK unit.",</p>
<p>"data": {</p>
<p>"lines": [</p>
<p>{"ref": "48211-1", "code": "REJECT_POCKET_OVER",</p>
<p>"pocket": {"level": "department", "name": "Pabrikasi", "wage_type": "non_upah",</p>
<p>"basis": "yearly", "limit": 75000000, "used": 52650000,</p>
<p>"after": 78150000, "pct_after": 104.2},</p>
<p>"account": {"budget": 30000000, "commitment": 12000000, "realization": 9000000,</p>
<p>"remain_commitment": 18000000, "remain_budget": 21000000,</p>
<p>"pct_commitment": 40.0, "ews": "green"}}</p>
<p>]</p>
<p>}</p>
<p>}</p></th>
</tr>
</thead>
<tbody>
</tbody>
</table>

*Nomor perkiraan, nama, dan angka pada contoh hanya ilustrasi.*

## 6. Spesifikasi Adaptor Odoo 10

### 6.1 Titik Pemanggilan

| **Model Odoo 10**                                      | **Metode / tombol**                       | **Layanan**    | **Perilaku**                                                                                                                                  |
|--------------------------------------------------------|-------------------------------------------|----------------|-----------------------------------------------------------------------------------------------------------------------------------------------|
| **logistik.spm.lines (ka_logistik_spm)**               | onchange perkiraan, HPS, kuantum, tanggal | API-02         | Tampilkan anggaran, sisa, %, warna; mengganti perhitungan PKAT lokal dan SQL sisa Kasi/Kabag                                                  |
| **logistik.pengajuan.spm**                             | Ajukan dan setiap persetujuan             | API-03         | WARN: alasan permintaan wajib, notifikasi ke atasan; lolos tanpa peringatan: persetujuan Kabag TUK dan PP dilewati dan dicatat sebagai sistem |
| **ka_spk (SPPJ/SPK)**                                  | Pilih perkiraan / Nomor Investasi; Ajukan | API-02, API-03 | Sama dengan SPM                                                                                                                               |
| **purchase.order**                                     | button_confirm (sebelum super)            | API-04         | REJECT: UserError berisi message, PO tetap draft. Nilai = price_subtotal per baris                                                            |
| **purchase.order**                                     | action_cancel                             | API-05         | Lepas serapan                                                                                                                                 |
| **stock.picking (bon barang)**                         | Mark as Todo / validasi pemakaian         | API-06         | Nilai = kuantum × harga standar; REJECT: UserError                                                                                            |
| **account.invoice (BA/NTB)**                           | action_invoice_open                       | API-06         | Nilai = subtotal baris tanpa pajak                                                                                                            |
| **ka_account.voucher**                                 | Posting kas/bank (hanya kas keluar)       | API-06         | Nilai = jumlah baris voucher                                                                                                                  |
| **account.move (memo/koreksi)**                        | post, untuk jurnal manual                 | API-06         | Nilai = debit pada perkiraan biaya/proyek                                                                                                     |
| **account.move**                                       | post, button_cancel, unlink               | API-07         | Kirim baris jurnal; gagal → antrean                                                                                                           |
| **account.account, ka_account.stasiun, hr.department** | create / write; cron harian               | API-08         | Sinkron master                                                                                                                                |

### 6.2 Ketentuan Adaptor

| **ID**    | **Spesifikasi**                                                                                                                                                                                                                                                                                       | **Ref. BRD** |
|-----------|-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|--------------|
| **AD-01** | Seluruh panggilan melalui satu kelas klien (pkat.connector) yang menambahkan header, kunci idempotensi, batas waktu, dan pencatatan log lokal. Modul transaksi tidak memanggil Odoo 20 langsung.                                                                                                      | IN-01        |
| **AD-02** | Konfigurasi per company di Odoo 10: alamat Odoo 20, token, batas waktu, sakelar aktif. Hanya dapat dilihat/diubah administrator.                                                                                                                                                                      | IN-05        |
| **AD-03** | Fail-closed: bila API-04 atau API-06 gagal terhubung/batas waktu/HTTP 5xx, transaksi ditolak dengan pesan "Layanan anggaran tidak dapat dihubungi". API-02/API-03 gagal: SPM/SPPJ tetap dapat diproses dengan tanda "anggaran belum diperiksa" dan tidak boleh memakai lewati-persetujuan otomatis.   | IN-04        |
| **AD-04** | Kompensasi: bila button_confirm gagal setelah API-04 berhasil (transaksi Odoo 10 di-rollback), adaptor mengirim API-05 melalui koneksi basis data terpisah; bila itu pun gagal, masuk antrean pembatalan.                                                                                             | IN-03        |
| **AD-05** | Antrean jurnal (pkat.journal.queue): baris yang gagal dikirim disimpan dan dikirim ulang oleh cron tiap 5 menit, berurutan per company. Sebelum API-06, adaptor mengirim dulu antrean company tersebut; bila antrean lebih tua dari 30 menit masih ada, transaksi realisasi ditolak.                  | IN-07        |
| **AD-06** | Rekonsiliasi: cron harian mengirim API-10 untuk bulan berjalan dan bulan sebelumnya.                                                                                                                                                                                                                  | IN-08        |
| **AD-07** | Cermin referensi: cron dan tombol manual memanggil API-01 lalu memperbarui logistik.pkrat.account dan logistik.pkrat (kode, nama, nilai) sebagai data baca-saja, agar field relasi yang ada pada SPM, SPK, tender, dan aset tetap berfungsi. Angka serapan, realisasi, dan sisa tidak disimpan lokal. | MG-06, IN-09 |
| **AD-08** | Hak akses: daftar PKAT yang dapat dipilih/dilihat pengguna unit di Odoo 10 disaring dengan hasil API-09 (disimpan sementara per sesi, maksimal 15 menit).                                                                                                                                             | IN-10        |
| **AD-09** | PO antar-company (PO Direksi yang disalin ke unit): serapan dicatat sekali, pada PO milik company pemilik anggaran; PO salinan dikirim dengan penanda agar tidak dicek ulang.                                                                                                                         | SR-02        |
| **AD-10** | Menu, cron, dan tombol ka_stock_account_pkrat dinonaktifkan; ka_logistik_pkrat menjadi baca-saja (kecuali sinkron AD-07); cron hitung realisasi lama dimatikan.                                                                                                                                       | MG-06        |

## 7. Antarmuka Pengguna (Odoo 20)

### 7.1 Struktur Menu

| **Menu**                                                    | **Isi**                                                                                                  |
|-------------------------------------------------------------|----------------------------------------------------------------------------------------------------------|
| **Dashboard**                                               | Tab Ringkasan, PKAT, Serapan Anggaran, Realisasi Biaya                                                   |
| **Anggaran \> PKAT Stasiun**                                | Daftar dan form pkat.budget beserta baris perkiraan dan rencana bulanan; tombol alur status; impor Excel |
| **Anggaran \> Nomor Investasi**                             | Daftar dan form pkat.project; alokasi tahun/bulan; realisasi fisik; tutup proyek                         |
| **Anggaran \> Kantung**                                     | Daftar pkat.pocket: batas, serapan, realisasi, %, warna, status kunci; kunci manual                      |
| **Permohonan \> Pergeseran & Tambahan**                     | Form permohonan multi-baris; tombol Ajukan, Setujui, Tolak, Proses; cetak formulir                       |
| **Buku \> Serapan (PO), Realisasi (Jurnal), Potensi (SPM)** | Daftar baca-saja dengan filter dan ekspor                                                                |
| **Laporan**                                                 | LP-01 s.d. LP-05                                                                                         |
| **Log**                                                     | Pemeriksaan, kunci, API, rekonsiliasi                                                                    |
| **Konfigurasi**                                             | Pengaturan per company/tahun, master perkiraan/stasiun/bagian, token API                                 |

### 7.2 Dashboard

| **ID**       | **Spesifikasi**                                                                                                                                                                                     | **Ref. BRD**     |
|--------------|-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|------------------|
| **UI-DB-01** | Filter bersama: unit, tahun, periode (bulan berjalan, s.d. bulan, triwulan, tahunan), bagian, seksi, stasiun, perkiraan, biaya/investasi, upah/non-upah, Nomor Investasi. Filter terbawa antar tab. | DB-01, DB-10     |
| **UI-DB-02** | Data disaring otomatis menurut area pengguna (8.2).                                                                                                                                                 | DB-02            |
| **UI-DB-03** | Tab Ringkasan: kartu Anggaran, Serapan, Realisasi, Sisa Serapan, Sisa Anggaran, Potensi serapan; tabel per kantung dengan status; daftar perhatian; progres permohonan.                             | DR-01 s.d. DR-04 |
| **UI-DB-04** | Tab PKAT: kartu PKAT awal/pergeseran/tambahan/berlaku; komposisi komponen; rencana bulanan; status pengesahan; riwayat perubahan; investasi.                                                        | DK-01 s.d. DK-06 |
| **UI-DB-05** | Tab Serapan: % serapan per kantung dengan garis 100%; tren vs rencana; 10 teratas; daftar PO dan PO ditolak; SPM diperingatkan; serapan proyek.                                                     | DS-01 s.d. DS-07 |
| **UI-DB-06** | Tab Realisasi: tren vs rencana dan tahun lalu; per sumber dokumen; selisih serapan − realisasi; upah/non-upah; fisik vs keuangan proyek; transaksi ditolak; BOPO.                                   | RB-01 s.d. RB-08 |
| **UI-DB-07** | Setiap angka dapat diklik sampai daftar dokumen; baris dokumen menampilkan nomor Odoo 10.                                                                                                           | DB-04            |
| **UI-DB-08** | Penanda "Sinkron terakhir" dari waktu journal/push terakhir per company; berwarna peringatan bila melebihi sync_stale_minutes.                                                                      | DB-05            |
| **UI-DB-09** | Ekspor Excel dan PDF mengikuti filter aktif.                                                                                                                                                        | DB-06            |

### 7.3 Laporan

| **ID**       | **Laporan**                                                                                                                                                                                                                  | **Parameter**                                                   |
|--------------|------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|-----------------------------------------------------------------|
| **UI-LP-01** | Anggaran, serapan, realisasi, sisa serapan, sisa anggaran per unit/bagian/stasiun/perkiraan                                                                                                                                  | Tahun, periode (MTD, YTD, tahunan), unit, bagian, upah/non-upah |
| **UI-LP-02** | Realisasi proyek investasi per Nomor Investasi dan jenis                                                                                                                                                                     | Tahun, periode (MTD, YTD), unit, jenis                          |
| **UI-LP-03** | Riwayat pergeseran, tambahan, penguncian, transaksi ditolak                                                                                                                                                                  | Rentang tanggal, unit                                           |
| **UI-LP-04** | Rencana barang, non-barang, investasi, PKAT                                                                                                                                                                                  | Tahun, unit, stasiun                                            |
| **UI-LP-05** | Realisasi Anggaran per unit: rekap per bagian dan rincian per stasiun, terpisah tenaga kerja dan non tenaga kerja; kolom realisasi bulan, PKAT bulan, %, realisasi s.d. bulan, PKAT s.d. bulan, %, PKAT total, %, saldo PKAT | Tahun, bulan, unit                                              |

## 8. Hak Akses dan Keamanan

### 8.1 Matriks Hak (B = baca, T = tulis, – = tidak ada)

| **Objek**                           | **Anggaran KD** | **TUK Unit** | **Pemimpin** | **Pengguna** | **Direksi** | **Auditor** | **Admin** |
|-------------------------------------|-----------------|--------------|--------------|--------------|-------------|-------------|-----------|
| **Konfigurasi anggaran**            | T               | B            | B            | –            | B           | B           | B         |
| **Master perkiraan/stasiun/bagian** | T               | B            | B            | B            | B           | B           | T         |
| **PKAT stasiun dan baris**          | T               | B            | B            | B            | B           | B           | B         |
| **Nomor Investasi**                 | T               | B            | B            | B            | B           | B           | B         |
| **Kantung (kunci manual)**          | T               | B            | B            | B            | B           | B           | B         |
| **Permohonan: buat/ajukan**         | B               | T            | B            | –            | B           | B           | B         |
| **Permohonan: setujui unit**        | –               | –            | T            | –            | –           | –           | –         |
| **Permohonan: proses tambahan**     | T               | –            | –            | –            | –           | –           | –         |
| **Buku serapan/realisasi/potensi**  | B               | B            | B            | B            | B           | B           | B         |
| **Log pemeriksaan dan kunci**       | B               | B            | B            | –            | B           | B           | B         |
| **Log API, token, rekonsiliasi**    | B               | –            | –            | –            | –           | B           | T         |

### 8.2 Aturan Data dan Keamanan

| **ID**    | **Spesifikasi**                                                                                                                                                                                                        | **Ref. BRD** |
|-----------|------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|--------------|
| **AK-01** | Record rule company pada semua model: pengguna hanya melihat company yang ditugaskan; Direksi, Bagian Anggaran KD, dan Auditor melihat semua.                                                                          | PK-09, NF-04 |
| **AK-02** | Record rule area untuk grup pkat_pengguna: Kasubsi melihat stasiun/sub seksinya, Kasi seksinya, Kabag bagiannya, berdasarkan pkat.department.manager_user_id dan turunannya.                                           | DB-02        |
| **AK-03** | Tidak ada ACL tanpa grup; tidak ada pemakaian superuser untuk membaca anggaran; seluruh query memakai ORM atau SQL berparameter.                                                                                       | NF-04        |
| **AK-04** | Pengguna API (pkat_api) hanya dapat mengakses controller API; tidak dapat login antarmuka.                                                                                                                             | NF-05        |
| **AK-05** | Layanan baca (API-01, API-02) menerapkan hak akses pengguna pada header X-PKAT-User; pengguna tidak dikenal → ERR_ACCESS. Layanan cek transaksi tidak dibatasi area, karena operator transaksi bukan pemilik anggaran. | IN-10        |
| **AK-06** | Pemisahan tugas: pengaju permohonan tidak dapat menyetujui permohonannya sendiri.                                                                                                                                      | SW-06        |
| **AK-07** | Perubahan field kunci (anggaran, status, konfigurasi, kunci manual) terekam di chatter dengan nilai lama dan baru.                                                                                                     | NF-06        |

## 9. Spesifikasi Non-Fungsional

| **ID**    | **Aspek**         | **Spesifikasi**                                                                                                                              |
|-----------|-------------------|----------------------------------------------------------------------------------------------------------------------------------------------|
| **NF-01** | Kinerja API       | Cek anggaran (API-03, 04, 06) selesai \< 2 detik termasuk jaringan untuk dokumen s.d. 50 baris; diuji dengan 20 pengguna bersamaan.          |
| **NF-02** | Kinerja dashboard | Setiap tab tampil ≤ 5 detik untuk data satu tahun satu unit; agregat dibaca dari field tersimpan, bukan dihitung dari buku saat tampil.      |
| **NF-03** | Konsistensi       | Dua PO bersamaan pada kantung yang sama tidak dapat membuat serapan melebihi batas (dibuktikan uji konkurensi TS-08).                        |
| **NF-04** | Ketersediaan      | Odoo 20 tersedia 24 jam selama musim giling; pemeliharaan terjadwal diumumkan karena transaksi Odoo 10 bersifat fail-closed.                 |
| **NF-05** | Pemulihan         | Backup harian basis data Odoo 20; setelah pemulihan, buku realisasi dapat dibangun ulang dari Odoo 10 dengan kirim ulang jurnal per periode. |
| **NF-06** | Jejak audit       | Log pemeriksaan, kunci, dan API disimpan minimal 2 tahun anggaran.                                                                           |
| **NF-07** | Kompatibilitas    | Adaptor berjalan pada Odoo 10 / Python 2.7 tanpa pustaka tambahan selain requests.                                                           |
| **NF-08** | Bahasa            | Antarmuka, pesan API, dan laporan berbahasa Indonesia.                                                                                       |
| **NF-09** | Pemantauan        | Layar admin menampilkan status koneksi tiap company, panjang antrean jurnal, galat API 24 jam terakhir, dan selisih rekonsiliasi.            |

## 10. Spesifikasi Migrasi Data

| **ID**    | **Data**                 | **Sumber Odoo 10**                                                                 | **Tujuan dan aturan**                                                                                                                 |
|-----------|--------------------------|------------------------------------------------------------------------------------|---------------------------------------------------------------------------------------------------------------------------------------|
| **MG-01** | Company, bagian/seksi    | res.company, hr.department                                                         | pkat.department; padanan kode; manajer dipadankan ke pengguna Odoo 20                                                                 |
| **MG-02** | Stasiun                  | ka_account.stasiun                                                                 | pkat.cost.center                                                                                                                      |
| **MG-03** | Perkiraan                | account.account (kode, stasiun, bagian, upah, tipe)                                | pkat.account; cost_item dari digit 7–8; unit_pocket dari rentang jenis biaya; is_spt ditetapkan Bagian Anggaran                       |
| **MG-04** | PKAT 2027                | File Excel unit                                                                    | Impor langsung di Odoo 20 (FS-PK-01)                                                                                                  |
| **MG-05** | Nomor Investasi berjalan | logistik.pkrat berstatus disetujui dan belum selesai                               | pkat.project dengan carry over = nilai − realisasi s.d. tanggal pisah; analytic dipetakan ke kode proyek; company dari bagian/stasiun |
| **MG-06** | Serapan awal             | PO terkonfirmasi yang belum selesai untuk proyek carry over dan PO bertanggal 2027 | pkat.commitment melalui API-04 mode migrasi (tanpa penolakan, ditandai)                                                               |
| **MG-07** | Realisasi awal proyek    | Jurnal posted s.d. tanggal pisah                                                   | Saldo awal pada pkat.project.year; dibandingkan dengan ka_logistik_pkrat                                                              |
| **MG-08** | Pengguna dan grup        | res.users, hr.employee                                                             | Akun Odoo 20 dan penugasan grup (2.3)                                                                                                 |

**Urutan pelaksanaan**

> 1\. Uji coba migrasi di lingkungan uji dengan salinan data produksi; rekonsiliasi dan perbaikan pemetaan.
>
> 2\. Pembekuan perubahan master perkiraan/stasiun di Odoo 10 menjelang go-live.
>
> 3\. Migrasi master, pengguna, lalu proyek carry over dan serapan awal.
>
> 4\. Impor dan pengesahan PKAT 2027.
>
> 5\. Pemasangan adaptor, penonaktifan ka_stock_account_pkrat, uji asap tiap titik transaksi.
>
> 6\. Persetujuan hasil rekonsiliasi oleh Bagian Anggaran Kantor Direksi.

## 11. Spesifikasi Pengujian

| **Tingkat**   | **Cakupan**                                                                                        | **Pelaksana dan acuan**          |
|---------------|----------------------------------------------------------------------------------------------------|----------------------------------|
| **Unit test** | Mesin pemeriksaan, perhitungan batas tiga dasar, validasi pergeseran, perhitungan realisasi proyek | Developer; otomatis; acuan bab 4 |
| **SIT**       | Alur ujung ke ujung Odoo 10 → API → Odoo 20, termasuk gangguan dan konkurensi                      | QA; acuan SRS (tabel di bawah)   |
| **UAT**       | Skenario bisnis di tiga unit                                                                       | Key user dan BPO; acuan BRD 8.3  |

**Skenario SIT wajib**

| **ID**    | **Skenario**                                                                                                              | **Hasil yang diharapkan**                                                                                        |
|-----------|---------------------------------------------------------------------------------------------------------------------------|------------------------------------------------------------------------------------------------------------------|
| **TS-01** | Contoh kasus BRD 2.6: kantung Rp100 juta, dasar yearly. Tahap 1–3: SPM 30/80/50 juta, PO 30/50/20 juta, bon 30/30/20 juta | SPM tahap 2 dan 3 diperingatkan; semua PO dan bon lolos; posisi akhir serapan 100%, realisasi 80%                |
| **TS-02** | Lanjutan: PO 20 juta dan bon 30 juta                                                                                      | PO ditolak REJECT_POCKET_OVER; bon ditolak; serapan tetap 100%                                                   |
| **TS-03** | Perkiraan tanpa anggaran pada SPM, PO, bon                                                                                | REJECT_NO_BUDGET pada ketiganya                                                                                  |
| **TS-04** | Perkiraan melebihi anggaran, kantung masih cukup                                                                          | WARN_ACCOUNT_OVER; transaksi berhasil                                                                            |
| **TS-05** | Ulangi TS-01/02 dengan dasar ytd dan mtd serta tingkat kantung perkiraan dan stasiun                                      | Keputusan sesuai rumus FS-CK-05                                                                                  |
| **TS-06** | PO PLB                                                                                                                    | Serapan bertambah pada Nomor PLB dan perkiraan biaya rutin; pembatalan melepas keduanya                          |
| **TS-07** | Pergeseran saat kantung terkunci: ajukan, setujui                                                                         | Anggaran berpindah; kunci terbuka; PO yang sama kini lolos; notifikasi ke Bagian Anggaran                        |
| **TS-08** | Dua PO bersamaan yang masing-masing cukup tetapi bersama melebihi batas                                                   | Tepat satu lolos                                                                                                 |
| **TS-09** | Kirim ulang permintaan yang sama (kunci idempotensi sama)                                                                 | Tidak ada serapan ganda; respons identik                                                                         |
| **TS-10** | Odoo 20 dimatikan: SPM, PO, bon                                                                                           | SPM lolos dengan tanda belum diperiksa; PO dan bon ditolak; setelah pulih antrean jurnal terkirim tanpa duplikat |
| **TS-11** | Konfirmasi PO gagal di Odoo 10 setelah serapan tercatat                                                                   | Serapan dibatalkan otomatis                                                                                      |
| **TS-12** | Jurnal posted, di-unpost, dihapus; rekonsiliasi harian                                                                    | Realisasi mengikuti; selisih rekonsiliasi nol                                                                    |
| **TS-13** | Tambahan investasi 4%, 8%, 12% kumulatif                                                                                  | Tier direksi, dekom, pemegang_saham; tidak dapat diproses tanpa data surat                                       |
| **TS-14** | Hak akses: Kasubsi, Kasi, Kabag, TUK unit, unit lain                                                                      | Hanya melihat area masing-masing di Odoo 20 dan daftar PKAT Odoo 10                                              |
| **TS-15** | Perkiraan Tebu SPT melebihi anggaran                                                                                      | Lolos tanpa kunci; tampil di dashboard                                                                           |
| **TS-16** | Kunci manual Bagian Anggaran                                                                                              | PO dan realisasi ditolak REJECT_MANUAL_LOCK sampai dibuka                                                        |
| **TS-17** | Laporan UI-LP-05 dibandingkan laporan Realisasi Anggaran Oktober 2026 dengan data yang sama                               | Angka sama per bagian dan stasiun                                                                                |

## 12. Asumsi Desain dan Keputusan Teknis

Butir berikut adalah pilihan desain tim analis yang tidak diatur rinci di BRD. Mohon dikonfirmasi saat review SRS:

| **No.** | **Asumsi / keputusan teknis**                                                                                                           | **Dampak bila berubah**                                          |
|---------|-----------------------------------------------------------------------------------------------------------------------------------------|------------------------------------------------------------------|
| **1**   | Nilai cek bon barang = kuantum × harga standar barang (seperti Odoo 10 saat ini), bukan nilai jurnal aktual.                            | Rumus AD pada stock.picking                                      |
| **2**   | PO valas dikonversi dengan kurs tanggal PO; selisih kurs saat pembayaran hanya memengaruhi realisasi.                                   | FS-SR-02                                                         |
| **3**   | PO antar-company dicatat sekali pada company pemilik anggaran (AD-09).                                                                  | Risiko serapan ganda                                             |
| **4**   | Revisi PO dilakukan dengan batal lalu terbit ulang (nomor berakhiran -B), sehingga serapan lama dilepas dan yang baru dicek ulang.      | Perlu layanan ubah nilai bila PO dapat diedit setelah konfirmasi |
| **5**   | Saat pergeseran/tambahan diproses, rencana bulanan disesuaikan proporsional dari bulan berjalan s.d. Desember bila bulan tidak dipilih. | Hasil dasar ytd dan mtd                                          |
| **6**   | Cek REALISASI untuk Berita Acara/NTB atas PO tetap membandingkan realisasi, terpisah dari serapan PO-nya.                               | FS-CK-06                                                         |
| **7**   | Padanan pengguna Odoo 10 ↔ Odoo 20 memakai login; bila berbeda, memakai NIK pegawai.                                                    | API-G-02, AD-08                                                  |
| **8**   | ka_logistik_pkrat dipertahankan sebagai cermin baca-saja agar relasi dokumen Odoo 10 tidak perlu diubah (AD-07).                        | Lingkup perubahan modul SPM, SPK, tender, aset                   |
| **9**   | Versi dan nama teknis modul Odoo 20 mengikuti standar pengembangan PDE.                                                                 | Penamaan saja                                                    |
| **10**  | Proyek bertipe Memorandum dan Rutin dimigrasikan apa adanya dan diperlakukan seperti Nomor Investasi lain.                              | FS-CK-09                                                         |

## Lampiran A. Matriks Ketertelusuran BRD → SRS

| **Kebutuhan BRD**           | **Spesifikasi SRS**                                                    |
|-----------------------------|------------------------------------------------------------------------|
| **PK-01 s.d. PK-14**        | DM-01 s.d. DM-06, FS-PK-01 s.d. FS-PK-09, MG-01 s.d. MG-05             |
| **SR-01 s.d. SR-09**        | DM-08 s.d. DM-10, FS-SR-01 s.d. FS-SR-09                               |
| **PP-01 s.d. PP-08**        | FS-CK-01 s.d. FS-CK-09, API-02, API-03, bab 6.1 (SPM, SPPJ)            |
| **PR-01 s.d. PR-14**        | FS-CK-01 s.d. FS-CK-14, API-04 s.d. API-06, bab 6.1, AD-03             |
| **LK-01 s.d. LK-05**        | DM-07, FS-LK-01 s.d. FS-LK-04                                          |
| **SW-01 s.d. SW-08**        | DM-11, FS-SW-01 s.d. FS-SW-08, AK-06                                   |
| **TA-01 s.d. TA-06**        | DM-11, FS-TA-01 s.d. FS-TA-05                                          |
| **IV-01 s.d. IV-04**        | DM-06, FS-IV-01 s.d. FS-IV-04, FS-SR-06                                |
| **EW-01 s.d. EW-04**        | FS-EW-01 s.d. FS-EW-03, FS-LK-04                                       |
| **DB, DR, DK, DS, RB**      | UI-DB-01 s.d. UI-DB-09, NF-02                                          |
| **LP-01 s.d. LP-05**        | UI-LP-01 s.d. UI-LP-05                                                 |
| **BR-01 s.d. BR-13**        | DM-04, FS-SR, FS-CK-05 s.d. FS-CK-09, FS-SW-02 s.d. FS-SW-05, FS-TA-03 |
| **NF-01 s.d. NF-08 (BRD)**  | Bab 8 dan bab 9, API-G-01 s.d. API-G-08                                |
| **MG-01 s.d. MG-07 (BRD)**  | Bab 10, AD-07, AD-10                                                   |
| **IN-01 s.d. IN-10**        | Bab 5, AD-01 s.d. AD-09, AK-05                                         |
| **Kriteria penerimaan 8.3** | TS-01, TS-02, TS-10, TS-12                                             |

## Lampiran B. Daftar Pesan Pengguna

| **Kode**                     | **Pesan (kerangka)**                                                                                                                                                                           |
|------------------------------|------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| **WARN_ACCOUNT_OVER**        | Perhatian: perkiraan {perkiraan} akan mencapai {persen}% dari anggarannya. Kantung {kantung} masih mencukupi, transaksi dapat dilanjutkan.                                                     |
| **WARN_POCKET_OVER**         | Perhatian: permintaan ini membuat potensi serapan kantung {kantung} menjadi {persen}%. Isi alasan permintaan. Pengajuan akan diteruskan ke atasan.                                             |
| **REJECT_NO_BUDGET**         | Transaksi tidak dapat diproses: perkiraan {perkiraan} tidak dianggarkan pada tahun {tahun}.                                                                                                    |
| **REJECT_POCKET_OVER**       | {Dokumen} tidak dapat diproses. {Serapan/Realisasi} kantung {kantung} akan menjadi {persen}% dari anggaran. Kekurangan Rp {kurang}. Ajukan pergeseran atau tambahan anggaran melalui TUK unit. |
| **REJECT_PROJECT_OVER**      | {Dokumen} tidak dapat diproses. Nomor Investasi {proyek} akan menjadi {persen}% dari anggaran. Kekurangan Rp {kurang}. Ajukan tambahan anggaran investasi.                                     |
| **REJECT_PROJECT_CLOSED**    | Nomor Investasi {proyek} sudah ditutup dan tidak menerima transaksi baru.                                                                                                                      |
| **REJECT_MANUAL_LOCK**       | Kantung {kantung} sedang dikunci oleh Bagian Anggaran Kantor Direksi: {alasan}.                                                                                                                |
| **Layanan tidak terjangkau** | Layanan anggaran tidak dapat dihubungi. Transaksi belum dapat diproses; coba beberapa saat lagi atau hubungi PDE.                                                                              |
