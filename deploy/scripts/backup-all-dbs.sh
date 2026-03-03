#!/bin/bash
set -euo pipefail

# Backup all PostgreSQL databases via docker exec pg_dump
# Output: deploy/backups/{service}-{YYYY-MM-DD-HHMMSS}.sql.gz

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
BACKUP_DIR="$REPO_ROOT/deploy/backups"
TIMESTAMP="$(date +%Y-%m-%d-%H%M%S)"

SERVICES=(identity course enrollment payment notification learning)

mkdir -p "$BACKUP_DIR"

failed=0
succeeded=0

for service in "${SERVICES[@]}"; do
    container="${service}-db"
    db_name="$service"
    db_user="${service}"
    backup_file="$BACKUP_DIR/${service}-${TIMESTAMP}.sql.gz"

    echo "Backing up ${service}..."

    if docker exec "$container" pg_dump -U "$db_user" "$db_name" 2>/dev/null | gzip > "$backup_file"; then
        size=$(du -h "$backup_file" | cut -f1)
        echo "  OK: ${backup_file} (${size})"
        ((succeeded++))
    else
        echo "  FAILED: ${service}"
        rm -f "$backup_file"
        ((failed++))
    fi
done

echo ""
echo "Backup complete: ${succeeded} succeeded, ${failed} failed"

if [ "$failed" -gt 0 ]; then
    exit 1
fi
