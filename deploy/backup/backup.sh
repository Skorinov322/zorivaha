#!/bin/sh
# =============================================================================
# Зори Ваха — MySQL Backup Script
# Runs inside the backup container via cron
# =============================================================================

set -e

TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_DIR="${BACKUP_DIR:-/backups}"
RETENTION_DAYS="${BACKUP_RETENTION_DAYS:-30}"
DB_HOST="${DB_HOST:-db}"
DB_PORT="${DB_PORT:-3306}"
DB_NAME="${DB_NAME:-zori_vaha}"
DB_USER="${DB_USER:-zori_vaha_user}"
FILENAME="${BACKUP_DIR}/db_${DB_NAME}_${TIMESTAMP}.sql.gz"

echo "=== Backup started: $(date) ==="
echo "Database: ${DB_NAME} @ ${DB_HOST}:${DB_PORT}"

mkdir -p "${BACKUP_DIR}"

# Dump and compress
mysqldump \
    --host="${DB_HOST}" \
    --port="${DB_PORT}" \
    --user="${DB_USER}" \
    --single-transaction \
    --quick \
    --routines \
    --triggers \
    "${DB_NAME}" | gzip -9 > "${FILENAME}"

SIZE=$(du -sh "${FILENAME}" | cut -f1)
echo "Backup created: ${FILENAME} (${SIZE})"

# Remove old backups
echo "Removing backups older than ${RETENTION_DAYS} days..."
find "${BACKUP_DIR}" -name "db_${DB_NAME}_*.sql.gz" \
    -mtime "+${RETENTION_DAYS}" -delete -print

echo "Current backups:"
ls -lh "${BACKUP_DIR}"/db_*.sql.gz 2>/dev/null || echo "  (none)"

echo "=== Backup finished: $(date) ==="
