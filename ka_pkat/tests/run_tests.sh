#!/bin/sh
# Jalankan di dalam container web_odoo20 (host tidak punya Python):
#   MSYS_NO_PATHCONV=1 docker exec web_odoo20 sh /mnt/extra-addons/ka_pkat/tests/run_tests.sh [tag]
# Meng-upgrade ka_pkat di DB uji lalu menjalankan test Odoo modul ini (transaksi di-rollback).
# Keluaran: baris log selain INFO (kosong = bersih) dan ringkasan jumlah test.
TAGS="${1:-/ka_pkat}"
DB="${PKAT_TEST_DB:-kebonagung}"
LOG=/tmp/ka_pkat_test.log
cd /mnt/extra-addons || exit 1
python3 ka_pkat/tests/test_engine.py 2>&1 | tail -3
odoo -c /etc/odoo/odoo.conf -d "$DB" -u ka_pkat --test-tags "$TAGS" --stop-after-init --http-port 18069 > "$LOG" 2>&1  # mode test tetap membuka HTTP; hindari bentrok 8069
grep -v ' INFO ' "$LOG" | grep -v 'markdown2 is not installed'
echo "--- ringkasan"
grep -E 'odoo.tests.result|tests in |ka_pkat: [0-9]+ tests' "$LOG" | tail -5
