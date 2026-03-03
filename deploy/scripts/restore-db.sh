#!/bin/bash
set -euo pipefail

# Restore a PostgreSQL database from a backup file
# Usage: restore-db.sh SERVICE BACKUP_FILE --confirm

VALID_SERVICES=(identity course enrollment payment notification learning)

usage() {
    echo "Usage: $0 SERVICE BACKUP_FILE --confirm"
    echo ""
    echo "  SERVICE      One of: ${VALID_SERVICES[*]}"
    echo "  BACKUP_FILE  Path to .sql.gz backup file"
    echo "  --confirm    Required safety flag (this drops and recreates the DB)"
    echo ""
    echo "Example:"
    echo "  $0 identity deploy/backups/identity-2026-03-03-120000.sql.gz --confirm"
    exit 1
}

if [ $# -lt 2 ]; then
    usage
fi

SERVICE="$1"
BACKUP_FILE="$2"
CONFIRM="${3:-}"

# Validate service name
valid=false
for s in "${VALID_SERVICES[@]}"; do
    if [ "$s" = "$SERVICE" ]; then
        valid=true
        break
    fi
done

if [ "$valid" = false ]; then
    echo "Error: unknown service '${SERVICE}'"
    echo "Valid services: ${VALID_SERVICES[*]}"
    exit 1
fi

# Validate backup file
if [ ! -f "$BACKUP_FILE" ]; then
    echo "Error: backup file not found: ${BACKUP_FILE}"
    exit 1
fi

# Require --confirm flag
if [ "$CONFIRM" != "--confirm" ]; then
    echo "WARNING: This will DROP and RECREATE the '${SERVICE}' database."
    echo "All existing data in '${SERVICE}' will be lost."
    echo ""
    echo "To proceed, re-run with --confirm:"
    echo "  $0 $SERVICE $BACKUP_FILE --confirm"
    exit 1
fi

container="${SERVICE}-db"
db_name="$SERVICE"
db_user="$SERVICE"

echo "Restoring ${SERVICE} from ${BACKUP_FILE}..."
echo "Dropping and recreating database '${db_name}'..."

# Drop connections and recreate DB
docker exec "$container" psql -U "$db_user" -d postgres -c \
    "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = '${db_name}' AND pid <> pg_backend_pid();" \
    > /dev/null 2>&1 || true

docker exec "$container" psql -U "$db_user" -d postgres -c "DROP DATABASE IF EXISTS ${db_name};"
docker exec "$container" psql -U "$db_user" -d postgres -c "CREATE DATABASE ${db_name} OWNER ${db_user};"

echo "Loading backup..."

if gunzip -c "$BACKUP_FILE" | docker exec -i "$container" psql -U "$db_user" -d "$db_name" > /dev/null 2>&1; then
    echo "OK: ${SERVICE} restored successfully"
else
    echo "FAILED: restore of ${SERVICE} encountered errors"
    exit 1
fi
