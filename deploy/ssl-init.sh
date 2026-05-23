#!/bin/bash
# =============================================================================
# Зори Ваха — Let's Encrypt SSL Certificate Initialization
# =============================================================================
# Run ONCE on first deploy to get SSL certificates.
# After that, certbot container auto-renews every 12 hours.
#
# Usage:
#   chmod +x deploy/ssl-init.sh
#   ./deploy/ssl-init.sh yourdomain.ru admin@yourdomain.ru
# =============================================================================

set -euo pipefail

DOMAIN="${1:-}"
EMAIL="${2:-}"

if [ -z "${DOMAIN}" ] || [ -z "${EMAIL}" ]; then
    echo "Usage: $0 <domain> <email>"
    echo "Example: $0 zorivaha.ru admin@zorivaha.ru"
    exit 1
fi

echo "=== SSL Init for ${DOMAIN} ==="

# Step 1: Start nginx with HTTP only (no SSL yet)
echo "Starting nginx for ACME challenge..."
docker compose up -d nginx

sleep 3

# Step 2: Get certificate
echo "Requesting certificate from Let's Encrypt..."
docker compose run --rm certbot certonly \
    --webroot \
    --webroot-path=/var/www/certbot \
    --email "${EMAIL}" \
    --agree-tos \
    --no-eff-email \
    --force-renewal \
    -d "${DOMAIN}" \
    -d "www.${DOMAIN}"

# Step 3: Update nginx config with domain
echo "Updating nginx config..."
sed -i "s/yourdomain.ru/${DOMAIN}/g" deploy/nginx/conf.d/zorivaha.conf

# Step 4: Reload nginx with SSL
echo "Reloading nginx with SSL..."
docker compose exec nginx nginx -s reload

echo ""
echo "=== SSL certificate obtained successfully! ==="
echo "Certificate: /etc/letsencrypt/live/${DOMAIN}/fullchain.pem"
echo "Auto-renewal: certbot container runs every 12 hours"
