#!/bin/sh
# Ekspor master Odoo 10 -> berkas CSV (PERUBAHAN_DESAIN_01 bagian 3 butir 6, K3).
# HANYA MEMBACA: sesi dibuka read-only (default_transaction_read_only=on) dan isinya SELECT.
# Tidak menyentuh container web_odoo10.
#
# Pakai (Git Bash, dari akar repo addons20):
#   sh ka_pkat/tools/export_master_odoo10.sh <nama_db_odoo10> [folder_keluaran]
# Bawaan folder keluaran: ka_pkat/master_odoo10 (di-.gitignore; berisi data perusahaan).
set -e
DB="$1"
OUT="${2:-ka_pkat/master_odoo10}"
[ -n "$DB" ] || { echo "nama database Odoo 10 wajib diisi"; exit 1; }
mkdir -p "$OUT"

q() {  # q <berkas> <sql>
    docker exec -e PGOPTIONS='-c default_transaction_read_only=on' db_odoo10 \
        sh -c "psql -U \"\${POSTGRES_USER:-odoo}\" -d \"$DB\" -v ON_ERROR_STOP=1 -c \"\\\\copy ($2) to stdout with csv header\"" \
        > "$OUT/$1"
    echo "$1: $(($(wc -l < "$OUT/$1") - 1)) baris"
}

q company.csv "select id, code, name from res_company order by id"

q department.csv "select d.id, d.name, d.code, d.parent_id, c.code as company_code, d.active, (select min(b.kode) from ka_account_bagian b where b.bagian_id = d.id) as bagian_kode from hr_department d join res_company c on c.id = d.company_id order by d.id"

q cost_center.csv "select s.id, s.kode, s.name, c.code as company_code, b.kode as bagian_kode, b.bagian_id as department_id, s.seksi_id, s.sub_seksi_id, s.active from ka_account_stasiun s join res_company c on c.id = s.company_id left join ka_account_bagian b on b.id = s.bagian_id order by s.id"

q account.csv "select a.id, a.code, a.name, c.code as company_code, a.parent_id, d.module || '.' || d.name as type_xmlid, t.name as type_name, t.type as type_internal, a.stasiun_id, a.bagian_id, a.upah, a.is_detail, a.deprecated from account_account a join res_company c on c.id = a.company_id join account_account_type t on t.id = a.user_type_id left join ir_model_data d on d.model = 'account.account.type' and d.res_id = t.id order by a.id"

q uom.csv "select u.id, u.name, g.name as category, u.uom_type, u.factor, u.active, (select count(*) from product_template t where t.uom_id = u.id) as product_count from product_uom u join product_uom_categ g on g.id = u.category_id order by u.id"

q product.csv "select t.id as tmpl_id, p.id as product_id, t.default_code, t.name, t.uom_id, u.name as uom_name, t.active from product_template t join product_product p on p.product_tmpl_id = t.id join product_uom u on u.id = t.uom_id order by t.id"
