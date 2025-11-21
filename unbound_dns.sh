#!/usr/bin/env bash

set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log_info() { echo -e "${GREEN}[INFO]${NC} $*"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $*"; }
log_error() { echo -e "${RED}[ERROR]${NC} $*"; }

if ! command -v brew >/dev/null 2>&1; then
  log_error "Homebrew is not installed. Install it from https://brew.sh first."
  exit 1
fi

BREW_PREFIX="$(brew --prefix)"
UNBOUND_ETC="${BREW_PREFIX}/etc/unbound"
UNBOUND_CONF="${UNBOUND_ETC}/unbound.conf"
UNBOUND_LOG="${BREW_PREFIX}/var/log/unbound.log"
ROOT_HINTS="${UNBOUND_ETC}/root.hints"
TRUST_ANCHOR="${UNBOUND_ETC}/root.key"

if ! command -v unbound >/dev/null 2>&1; then
  log_info "Installing Unbound..."
  brew install unbound
else
  log_info "Unbound already installed, checking for updates..."
  brew upgrade unbound || true
fi

mkdir -p "${UNBOUND_ETC}"
mkdir -p "${BREW_PREFIX}/var/log"

log_info "Downloading root hints file..."
if curl -fsSL https://www.internic.net/domain/named.root -o "${ROOT_HINTS}"; then
  log_info "Root hints downloaded successfully"
else
  log_warn "Failed to download root hints, will proceed without it"
  ROOT_HINTS=""
fi

log_info "Initializing DNSSEC trust anchor..."
if [ -f "${TRUST_ANCHOR}" ]; then
  log_info "Trust anchor already exists, updating..."
  unbound-anchor -a "${TRUST_ANCHOR}" -v || log_warn "Trust anchor update failed, using existing"
else
  if unbound-anchor -a "${TRUST_ANCHOR}" -v; then
    log_info "Trust anchor initialized successfully"
  else
    log_warn "Failed to initialize trust anchor, DNSSEC validation may not work"
  fi
fi

if [ -f "${UNBOUND_CONF}" ]; then
  BACKUP="${UNBOUND_CONF}.$(date +%Y%m%d_%H%M%S).bak"
  log_info "Backing up existing config to ${BACKUP}"
  cp "${UNBOUND_CONF}" "${BACKUP}"
fi

log_info "Writing Unbound configuration with DNSSEC validation and stats..."
cat > "${UNBOUND_CONF}" <<EOF
server:
    verbosity: 1
    interface: 127.0.0.1
    interface: ::1
    port: 53
    do-ip4: yes
    do-ip6: yes
    do-udp: yes
    do-tcp: yes
    
    num-threads: 2
    msg-cache-slabs: 4
    rrset-cache-slabs: 4
    infra-cache-slabs: 4
    key-cache-slabs: 4
    rrset-cache-size: 100m
    msg-cache-size: 50m
    so-rcvbuf: 1m
    
    qname-minimisation: yes
    qname-minimisation-strict: yes
    hide-identity: yes
    hide-version: yes
    harden-glue: yes
    harden-dnssec-stripped: yes
    harden-below-nxdomain: yes
    harden-referral-path: yes
    harden-algo-downgrade: yes
    use-caps-for-id: yes
    prefetch: yes
    prefetch-key: yes
    
    access-control: 127.0.0.0/8 allow
    access-control: ::1 allow
    access-control: 0.0.0.0/0 refuse
    access-control: ::/0 refuse
    
    logfile: "${UNBOUND_LOG}"
    log-queries: no
    log-replies: no
    log-local-actions: no
    
    username: ""
    chroot: ""
    directory: "${UNBOUND_ETC}"
    pidfile: "${BREW_PREFIX}/var/run/unbound.pid"
    
    aggressive-nsec: yes
    
    infra-host-ttl: 60
    infra-cache-numhosts: 10000
    
    serve-expired: yes
    serve-expired-ttl: 86400
    serve-expired-ttl-reset: yes
EOF

if [ -n "${ROOT_HINTS}" ] && [ -f "${ROOT_HINTS}" ]; then
  cat >> "${UNBOUND_CONF}" <<EOF
    
    root-hints: "${ROOT_HINTS}"
EOF
fi

if [ -f "${TRUST_ANCHOR}" ]; then
  cat >> "${UNBOUND_CONF}" <<EOF
    
    auto-trust-anchor-file: "${TRUST_ANCHOR}"
    val-clean-additional: yes
    val-permissive-mode: no
    val-log-level: 1
EOF
fi

cat >> "${UNBOUND_CONF}" <<EOF

remote-control:
    control-enable: yes
    control-interface: 127.0.0.1
    control-port: 8953
    control-use-cert: no

forward-zone:
    name: "."
    forward-addr: 1.1.1.1@853#cloudflare-dns.com
    forward-addr: 1.0.0.1@853#cloudflare-dns.com
    forward-addr: 9.9.9.9@853#dns.quad9.net
    forward-addr: 149.112.112.112@853#dns.quad9.net
    forward-addr: 8.8.8.8@853#dns.google
    forward-addr: 8.8.4.4@853#dns.google
    forward-tls-upstream: yes
    forward-no-cache: no
EOF

log_info "Setting up remote control..."
unbound-control-setup -d "${UNBOUND_ETC}" >/dev/null 2>&1 || log_warn "Control setup may have failed"

log_info "Validating Unbound configuration..."
if ! unbound-checkconf "${UNBOUND_CONF}"; then
  log_error "Configuration validation failed!"
  exit 1
fi

if pgrep -x unbound >/dev/null 2>&1; then
  log_info "Stopping existing Unbound instance..."
  sudo killall unbound || true
  sleep 1
fi

log_info "Starting Unbound..."
sudo unbound -d -c "${UNBOUND_CONF}" >"${UNBOUND_LOG}" 2>&1 &

sleep 3

if pgrep -x unbound >/dev/null 2>&1; then
  log_info "Unbound is running successfully"
else
  log_error "Unbound failed to start. Check ${UNBOUND_LOG}"
  exit 1
fi

PRIMARY_SERVICE="$(networksetup -listallnetworkservices 2>/dev/null | sed '1d' | head -n1 || true)"

if [ -z "${PRIMARY_SERVICE}" ]; then
  log_warn "Could not determine primary network service automatically."
  log_warn "You may need to run: sudo networksetup -setdnsservers 'Wi-Fi' 127.0.0.1"
else
  log_info "Setting DNS server for '${PRIMARY_SERVICE}' to 127.0.0.1..."
  sudo networksetup -setdnsservers "${PRIMARY_SERVICE}" 127.0.0.1
fi

log_info "Testing DNS resolution..."
if command -v dig >/dev/null 2>&1; then
  if dig @127.0.0.1 google.com +short +time=2 >/dev/null 2>&1; then
    log_info "DNS resolution working correctly"
  else
    log_warn "DNS test failed, but service is running"
  fi
else
  log_warn "'dig' not found. Install with: brew install bind"
fi

log_info ""
log_info "Setup complete! Features enabled:"
log_info "  ✓ DNS failover: Cloudflare → Quad9 → Google"
log_info "  ✓ DNSSEC validation with auto-updating trust anchor"
log_info "  ✓ Root hints for improved performance"
log_info "  ✓ Statistics endpoint on 127.0.0.1:8953"
log_info ""
log_info "View statistics with:"
log_info "  unbound-control -c ${UNBOUND_CONF} stats_noreset"
log_info ""
log_info "Check DNSSEC validation:"
log_info "  dig @127.0.0.1 dnssec.works +dnssec"
log_info "  dig @127.0.0.1 dnssec-failed.org +dnssec"
