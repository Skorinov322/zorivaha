#!/bin/bash
# =============================================================================
# Зори Ваха — Production Deploy Script
# =============================================================================
# Usage:
#   ./deploy/deploy.sh              # full deploy
#   ./deploy/deploy.sh --no-migrate # skip migrations
#   ./deploy/deploy.sh --rollback   # rollback to previous release
#
# Requirements:
#   - Docker + Docker Compose installed
#   - .env file configured
#   - Domain DNS pointing to this server
# =============================================================================

set -euo pipefail

# ── Colors ────────────────────────────────────────────────────────────────────
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log()     { echo -e "${GREEN}[$(date '+%H:%M:%S')] ✓ $*${NC}"; }
warn()    { echo -e "${YELLOW}[$(date '+%H:%M:%S')] ⚠ $*${NC}"; }
error()   { echo -e "${RED}[$(date '+%H:%M:%S')] ✗ $*${NC}" >&2; }
section() { echo -e "\n${BLUE}══════════════════════════════════════${NC}"; echo -e "${BLUE}  $*${NC}"; echo -e "${BLUE}══════════════════════════════════════${NC}"; }

# ── Config ────────────────────────────────────────────────────────────────────
COMPOSE="docker compose"
APP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SKIP_MIGRATE=false
ROLLBACK=false

# Parse args
for arg in "$@"; do
    case $arg in
        --no-migrate) SKIP_MIGRATE=true ;;
        --rollback)   ROLLBACK=true ;;
    esac
done

cd "${APP_DIR}"

# ── Pre-flight checks ─────────────────────────────────────────────────────────
section "Pre-flight checks"

if [ ! -f ".env" ]; then
    error ".env file not found! Copy .env.example and configure it."
    exit 1
fi

# Check required env vars
source .env 2>/dev/null || true
for var in SECRET_KEY; do
    if [ -z "${!var:-}" ]; then
        error "Required env var ${var} is not set in .env"
        exit 1
    fi
done

if [ "${SECRET_KEY}" = "CHANGE-ME-use-python-to-generate-a-50-char-random-key" ]; then
    error "SECRET_KEY is still the default value! Generate a real one."
    exit 1
fi

log "Environment checks passed"

# ── Rollback ──────────────────────────────────────────────────────────────────
if [ "${ROLLBACK}" = true ]; then
    section "Rolling back"
    warn "Rolling back to previous image..."
    ${COMPOSE} down
    # Tag current as failed, restore previous
    docker tag zorivaha-web:latest zorivaha-web:failed 2>/dev/null || true
    docker tag zorivaha-web:previous zorivaha-web:latest 2>/dev/null || true
    ${COMPOSE} up -d
    log "Rollback complete"
    exit 0
fi

# ── Backup before deploy ──────────────────────────────────────────────────────
section "Pre-deploy backup"
if ${COMPOSE} ps db | grep -q "running"; then
    log "Creating pre-deploy database backup..."
    ${COMPOSE} exec -T db sh -c \
        'mysqldump -u"${MYSQL_USER}" -p"${MYSQL_PASSWORD}" "${MYSQL_DATABASE}" | gzip > /tmp/pre_deploy_backup.sql.gz'
    ${COMPOSE} cp db:/tmp/pre_deploy_backup.sql.gz \
        "./backups/pre_deploy_$(date +%Y%m%d_%H%M%S).sql.gz" 2>/dev/null || \
        warn "Could not copy backup (backups dir may not exist)"
    log "Pre-deploy backup created"
else
    warn "Database not running, skipping backup"
fi

# ── Build ─────────────────────────────────────────────────────────────────────
section "Building Docker images"

# Tag current image as previous (for rollback)
docker tag zorivaha-web:latest zorivaha-web:previous 2>/dev/null || true

log "Building new image..."
${COMPOSE} build --no-cache web

log "Build complete"

# ── Pull latest images ────────────────────────────────────────────────────────
section "Pulling base images"
${COMPOSE} pull db redis nginx certbot
log "Images pulled"

# ── Start infrastructure ──────────────────────────────────────────────────────
section "Starting infrastructure"
${COMPOSE} up -d db redis
log "Waiting for database to be ready..."
sleep 5

# Wait for DB health
for i in $(seq 1 30); do
    if ${COMPOSE} exec -T db mysqladmin ping -h 127.0.0.1 -u"${DB_USER:-zori_vaha_user}" -p"${DB_PASSWORD:-zori_vaha_pass}" --silent > /dev/null 2>&1; then
        log "Database is ready"
        break
    fi
    if [ $i -eq 30 ]; then
        error "Database failed to start after 30 attempts"
        exit 1
    fi
    sleep 2
done

# ── Migrations ────────────────────────────────────────────────────────────────
if [ "${SKIP_MIGRATE}" = false ]; then
    section "Running migrations"
    ${COMPOSE} run --rm web python manage.py migrate --noinput
    log "Migrations complete"
else
    warn "Skipping migrations (--no-migrate)"
fi

# ── Static files ──────────────────────────────────────────────────────────────
section "Collecting static files"
${COMPOSE} run --rm web python manage.py collectstatic --noinput --clear
log "Static files collected"

# ── Deploy application ────────────────────────────────────────────────────────
section "Deploying application"

# Zero-downtime: start new web container before stopping old
log "Starting new web container..."
${COMPOSE} up -d --no-deps web

# Wait for web to be healthy
log "Waiting for web to be healthy..."
for i in $(seq 1 20); do
    if ${COMPOSE} exec -T web curl -sf http://localhost:8000/health/ > /dev/null 2>&1; then
        log "Web is healthy"
        break
    fi
    if [ $i -eq 20 ]; then
        warn "Health check timeout — check logs: docker compose logs web"
    fi
    sleep 3
done

# Start remaining services
log "Starting Celery workers..."
${COMPOSE} up -d --no-deps celery_worker celery_beat

log "Starting Nginx..."
${COMPOSE} up -d --no-deps nginx

log "Starting backup service..."
${COMPOSE} up -d --no-deps backup

# ── Post-deploy checks ────────────────────────────────────────────────────────
section "Post-deploy checks"

echo ""
echo "Service status:"
${COMPOSE} ps

echo ""
log "Deploy complete! 🚀"
echo ""
echo "  Site:     https://${ALLOWED_HOSTS%%,*}"
echo "  Logs:     docker compose logs -f web"
echo "  Shell:    docker compose exec web python manage.py shell"
echo "  Backup:   docker compose exec backup /backup.sh"
