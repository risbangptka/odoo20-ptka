# ka_base: port Odoo 10 → Odoo 20

Versi `10.0.0.1` → `20.0.1.0.0`. Sumber: `G:\Docker\addons\ka_base`.

## Perubahan

| Bagian | Odoo 10 | Odoo 20 |
|---|---|---|
| `res.company` name_search | override `name_search` | `_rec_names_search = ['code', 'name']` |
| `res.company` name_get | override `name_get` | `_compute_display_name` → tetap "code nama" |
| `res.partner.get_company_ref` | `@api.one`, return list | return recordset (`limit=1`); `[0]` masih jalan |
| `res.users` default `groups_id` | override (salin `base.default_user`) | **dihapus**, core sudah pakai `base.default_user_group` (KB-05) |
| `res.users.operating_unit_ids` | relation otomatis | relation dikunci `res_partner_res_users_rel` (sama dengan tabel Odoo 10) |
| ACL | `ir.model.access.csv`, grup kosong | `ir.access.csv` (model baru Odoo 20); grup kosong = *restriction*, jadi pakai `base.group_everyone` |
| Arsip provinsi | `toggle_active` + `boolean_button` | ribbon "Archived" + filter Archived di pencarian |
| Data induk | `views/ka_base_data.xml` | `data/ka_base_data.xml` |
| xmlid partner/company/user KA | `base.xxx` | **`ka_base.xxx`**, dipindah oleh `migrations/20.0.1.0.0/pre-migrate.py` (KB-02) |
| Password 6 user sistem | plaintext di XML | **dihapus** (KB-01) |
| `state_id eval="622"` | id DB | `base.state_id_ji` / `base.state_id_jt` |
| `image`, `fax`, `supplier`, `groups_id` | | `image_1920`/`logo`, dihapus, dihapus, `group_ids` |
| User R/K, internal, automated (KB-04) | default `SUPERUSER_ID` | **tanpa default**; ambil lewat `get_intercompany_user()`, `get_automated_system_user()`, `get_internal_user()` yang memberi `UserError` jelas bila kosong. Field di tab Setting R/K kini editable |
| `res.company.code` (KB-07) | `size=1` | `size=4`; kolom otomatis melebar saat upgrade, nilai lama tetap |
| Label `new_city` | "City" (bentrok dengan `city`) | "Kota/Kabupaten" |
| `tools/module_paths.py` | Python 2 | Python 3 (`os.makedirs(exist_ok=True)`), API tetap |

## Dampak ke modul lain saat di-port

- Ganti rujukan `base.pg_kebonagung`, `base.pg_trangkil`, `base.kantor_direksi`,
  `base.ou_*`, `base.user_*` → `ka_base.<nama yang sama>`
  (mis. `ka_tanaman/data/ir_sequence.xml`, `ka_analisa_qc/data/res_users_silab.xml`).
- `x.get_company_ref()[0]` → cukup `x.get_company_ref()`. Kalau company tidak ketemu,
  `[0]` sekarang melempar `IndexError` (dulu diam-diam recordset kosong).
- `operating_unit_default_get(self._uid)` → `operating_unit_default_get(self.env.uid)`.
- `sudo(user_id)` → `with_user(user_id)`.

## Belum diubah (butuh keputusan pemilik)

- **KB-08/09**: `new_city` dan `res.city.state` tetap ada berdampingan dengan `city`.

## Catatan keputusan KB-04 / KB-07 (2026-10-14)

- KB-04 opsi B: company tanpa user sistem akan error saat proses R/K/otomatis jalan,
  bukan lagi diam-diam sebagai superuser. Nilai di DB hasil migrasi tidak diubah;
  PT KEBON AGUNG (code 0) di produksi masih menunjuk user id 1, yang sejak Odoo 12
  adalah `__system__`. Tinjau setelah OpenUpgrade selesai.
- KB-07: kode >1 karakter ikut memperpanjang kode akun dari
  `ka_account/models/chart_template.py` (`code.replace("U", company.code)`) dan
  xmlid sequence `...unit.<code>` di ka_spt/ka_tanaman. Cek saat modul itu di-port.

## Uji yang sudah dilakukan (web_odoo20, 2026-10-14)

- Install di DB kosong: bersih, tanpa warning dari ka_base.
- Simulasi DB hasil migrasi (xmlid `base.*`, versi `10.0.0.1`) lalu `-u ka_base`:
  12 xmlid dipindah, company/user tidak duplikat.
- odoo shell: display name "code nama", pencarian kode "2", `get_company_ref`,
  `operating_unit_default_get`, compute Unit/PG, grup default user baru = internal,
  arsip provinsi, helper `module_file`, ACL `res.city.state`.
- KB-04: company baru tanpa user sistem -> ketiga `get_*_user()` memberi UserError.
- KB-07: kolom `varchar(1)` -> `varchar(4)` saat `-u`, kode `PGU1` bisa dicari, 5 karakter ditolak.
- **Belum** diuji terhadap data asli: menunggu DB hasil OpenUpgrade sampai versi 20.
