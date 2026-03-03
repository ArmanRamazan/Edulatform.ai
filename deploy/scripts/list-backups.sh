#!/bin/bash
set -euo pipefail

# List all database backups sorted by date

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKUP_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)/deploy/backups"

if [ ! -d "$BACKUP_DIR" ] || [ -z "$(ls -A "$BACKUP_DIR"/*.sql.gz 2>/dev/null)" ]; then
    echo "No backups found in ${BACKUP_DIR}"
    exit 0
fi

printf "%-14s %-22s %10s  %s\n" "SERVICE" "TIMESTAMP" "SIZE" "FILE"
printf "%-14s %-22s %10s  %s\n" "-------" "---------" "----" "----"

ls -1t "$BACKUP_DIR"/*.sql.gz 2>/dev/null | while read -r file; do
    basename=$(basename "$file")
    # Parse: {service}-{YYYY-MM-DD-HHMMSS}.sql.gz
    service="${basename%%-[0-9][0-9][0-9][0-9]-*}"
    timestamp="${basename#"${service}-"}"
    timestamp="${timestamp%.sql.gz}"
    size=$(du -h "$file" | cut -f1)
    printf "%-14s %-22s %10s  %s\n" "$service" "$timestamp" "$size" "$file"
done
