#!/bin/bash
# =============================================================================
# Зори Ваха — Database Restore Script
# Usage: ./restore.sh /backups/db_zori_vaha_20250101_030000.sql.gz
# =============================================================================

set -euo pipefail

BACKUP_FILE="${1:-}"
DB_HOST="${DB_HOST:-db}"
DB_PORT="${DB_PORT:-3306}"
DB_NAME="${DB_NAME:-zori_vaha}"
DB_USER="${DB_USER:-zori_vaha_user}"

if [ -z "${BACKUP_FILE}" ]; then
    echo "Usage: $0 <backup_file.sql.gz>"
    echo ""
    echo "Available backups:"
    ls -lh /backups/db_*.sql.gz 2>/dev/null || echo "  No backups found"
    exit 1
fi

if [ ! -f "${BACKUP_FILE}" ]; then
    echo "ERROR: Backup file not found: ${BACKUP_FILE}"
    exit 1
fi

echo "=== Restore started: $(date) ==="
echo "File:     ${BACKUP_FILE}"
echo "Database: ${DB_NAME} @ ${DB_HOST}:${DB_PORT}"
echo ""
echo "WARNING: This will DROP and recreate the database!"
read -p "Type 'yes' to continue: " CONFIRM

if [ "${CONFIRM}" != "yes" ]; then
    echo "Aborted."
    exit 0
fi

# Drop and recreate
echo "Dropping existing database..."
mysql --host="${DB_HOST}" --port="${DB_PORT}" \
      --user="${DB_USER}" \
      -e "DROP DATABASE IF EXISTS \`${DB_NAME}\`; CREATE DATABASE \`${DB_NAME}\` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"

# Restore
echo "Restoring from backup..."
gunzip -c "${BACKUP_FILE}" | mysql \
    --host="${DB_HOST}" \
    --port="${DB_PORT}" \
    --user="${DB_USER}" \
    "${DB_NAME}"

echo "=== Restore completed: $(date) ==="
