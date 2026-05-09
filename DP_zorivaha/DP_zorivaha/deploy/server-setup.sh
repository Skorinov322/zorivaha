#!/bin/bash
# =============================================================================
# Зори Ваха — Server Initial Setup Script
# =============================================================================
# Run ONCE on a fresh Ubuntu 22.04 / Debian 12 server.
# Installs Docker, creates user, configures firewall.
#
# Usage (as root):
#   curl -fsSL https://raw.githubusercontent.com/.../server-setup.sh | bash
#   # OR
#   chmod +x deploy/server-setup.sh && sudo ./deploy/server-setup.sh
# =============================================================================

set -euo pipefail

APP_USER="zorivaha"
APP_DIR="/var/www/zorivaha"

echo "=== Зори Ваха Server Setup ==="
echo "OS: $(lsb_release -ds 2>/dev/null || cat /etc/os-release | grep PRETTY_NAME | cut -d= -f2)"

# ── System update ─────────────────────────────────────────────────────────────
echo ""
echo "→ Updating system packages..."
apt-get update -qq
apt-get upgrade -y -qq
apt-get install -y -qq \
    curl wget git unzip \
    ufw fail2ban \
    htop iotop \
    logrotate

# ── Docker ────────────────────────────────────────────────────────────────────
echo ""
echo "→ Installing Docker..."
if ! command -v docker &>/dev/null; then
    curl -fsSL https://get.docker.com | sh
    systemctl enable docker
    systemctl start docker
    echo "Docker installed: $(docker --version)"
else
    echo "Docker already installed: $(docker --version)"
fi

# ── App user ──────────────────────────────────────────────────────────────────
echo ""
echo "→ Creating app user: ${APP_USER}..."
if ! id "${APP_USER}" &>/dev/null; then
    useradd --system --shell /bin/bash --create-home \
            --home-dir "/home/${APP_USER}" "${APP_USER}"
fi
usermod -aG docker "${APP_USER}"

# ── App directory ─────────────────────────────────────────────────────────────
echo ""
echo "→ Creating app directory: ${APP_DIR}..."
mkdir -p "${APP_DIR}"
mkdir -p "${APP_DIR}/backups"
mkdir -p /var/log/zorivaha
chown -R "${APP_USER}:${APP_USER}" "${APP_DIR}" /var/log/zorivaha

# ── Firewall ──────────────────────────────────────────────────────────────────
echo ""
echo "→ Configuring UFW firewall..."
ufw --force reset
ufw default deny incoming
ufw default allow outgoing
ufw allow ssh
ufw allow 80/tcp
ufw allow 443/tcp
ufw --force enable
echo "Firewall status:"
ufw status

# ── Fail2ban ──────────────────────────────────────────────────────────────────
echo ""
echo "→ Configuring fail2ban..."
cat > /etc/fail2ban/jail.local << 'EOF'
[DEFAULT]
bantime  = 3600
findtime = 600
maxretry = 5

[sshd]
enabled = true
port    = ssh
logpath = %(sshd_log)s

[nginx-http-auth]
enabled = true
EOF
systemctl enable fail2ban
systemctl restart fail2ban

# ── Swap (if < 2GB RAM) ───────────────────────────────────────────────────────
TOTAL_RAM=$(free -m | awk '/^Mem:/{print $2}')
if [ "${TOTAL_RAM}" -lt 2048 ] && [ ! -f /swapfile ]; then
    echo ""
    echo "→ Creating 2GB swap (RAM: ${TOTAL_RAM}MB)..."
    fallocate -l 2G /swapfile
    chmod 600 /swapfile
    mkswap /swapfile
    swapon /swapfile
    echo '/swapfile none swap sw 0 0' >> /etc/fstab
    sysctl vm.swappiness=10
    echo 'vm.swappiness=10' >> /etc/sysctl.conf
fi

# ── Logrotate ─────────────────────────────────────────────────────────────────
cat > /etc/logrotate.d/zorivaha << 'EOF'
/var/log/zorivaha/*.log {
    daily
    missingok
    rotate 14
    compress
    delaycompress
    notifempty
    create 0640 zorivaha zorivaha
    sharedscripts
    postrotate
        systemctl reload zorivaha-web 2>/dev/null || true
    endscript
}
EOF

# ── SSH hardening ─────────────────────────────────────────────────────────────
echo ""
echo "→ Hardening SSH..."
sed -i 's/#PasswordAuthentication yes/PasswordAuthentication no/' /etc/ssh/sshd_config
sed -i 's/PasswordAuthentication yes/PasswordAuthentication no/' /etc/ssh/sshd_config
systemctl reload sshd

echo ""
echo "=== Server setup complete! ==="
echo ""
echo "Next steps:"
echo "  1. Copy your SSH public key to /home/${APP_USER}/.ssh/authorized_keys"
echo "  2. Clone the project to ${APP_DIR}"
echo "  3. Configure .env file"
echo "  4. Run: cd ${APP_DIR} && ./deploy/ssl-init.sh yourdomain.ru admin@yourdomain.ru"
echo "  5. Run: ./deploy/deploy.sh"
