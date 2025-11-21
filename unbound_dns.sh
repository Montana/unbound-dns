#!/usr/bin/env bash

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

LOG_FILE="/tmp/unbound_install.log"

print_banner() {
    echo -e "${BLUE}"
    cat << "EOF"
╔══════════════════════════════════════════════════════════════╗
║              UNBOUND DNS INSTALLER                           ║
║  Resilient DNS with Automatic Failover & Survival Mode      ║
╚══════════════════════════════════════════════════════════════╝
EOF
    echo -e "${NC}"
}

log() {
    echo -e "${GREEN}[INFO]${NC} $1"
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] $1" >> "$LOG_FILE"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1"
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] ERROR: $1" >> "$LOG_FILE"
    exit 1
}

warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] WARN: $1" >> "$LOG_FILE"
}

success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

detect_os() {
    if [[ "$OSTYPE" == "darwin"* ]]; then
        OS="macos"
        log "Detected macOS"
    elif [[ -f /etc/os-release ]]; then
        . /etc/os-release
        case $ID in
            ubuntu|debian|pop|linuxmint)
                OS="debian"
                log "Detected Debian-based Linux: $PRETTY_NAME"
                ;;
            fedora|rhel|centos|rocky|almalinux)
                OS="redhat"
                log "Detected Red Hat-based Linux: $PRETTY_NAME"
                ;;
            arch|manjaro)
                OS="arch"
                log "Detected Arch-based Linux: $PRETTY_NAME"
                ;;
            *)
                error "Unsupported Linux distribution: $ID"
                ;;
        esac
    else
        error "Unable to detect operating system"
    fi
}

check_root() {
    if [[ $EUID -ne 0 ]] && [[ "$OS" != "macos" ]]; then
        error "This script must be run as root on Linux. Use: sudo $0"
    fi
    
    if [[ "$OS" == "macos" ]]; then
        log "Running on macOS - will request sudo when needed"
    fi
}

check_port_53() {
    log "Checking if port 53 is available..."
    
    if command -v lsof &> /dev/null; then
        PORT_CHECK=$(sudo lsof -i :53 -sTCP:LISTEN -t 2>/dev/null || true)
    elif command -v ss &> /dev/null; then
        PORT_CHECK=$(sudo ss -tlnp | grep :53 || true)
    else
        warn "Cannot check port 53 availability (lsof/ss not found)"
        return
    fi
    
    if [[ -n "$PORT_CHECK" ]]; then
        error "Port 53 is already in use. Stop the conflicting service first:
        macOS: sudo killall -9 mDNSResponder
        Linux (systemd-resolved): sudo systemctl stop systemd-resolved
        Linux (dnsmasq): sudo systemctl stop dnsmasq"
    fi
    
    log "Port 53 is available"
}

install_unbound_macos() {
    log "Installing Unbound on macOS via Homebrew..."
    
    if ! command -v brew &> /dev/null; then
        error "Homebrew is not installed. Install it from https://brew.sh"
    fi
    
    brew update
    brew install unbound
    
    UNBOUND_DIR="$(brew --prefix)/etc/unbound"
    UNBOUND_LOG="$(brew --prefix)/var/log/unbound.log"
    UNBOUND_PID="$(brew --prefix)/var/run/unbound.pid"
    UNBOUND_CONF="$UNBOUND_DIR/unbound.conf"
    
    mkdir -p "$UNBOUND_DIR"
    mkdir -p "$(dirname $UNBOUND_LOG)"
    mkdir -p "$(dirname $UNBOUND_PID)"
    
    success "Unbound installed successfully"
}

install_unbound_debian() {
    log "Installing Unbound on Debian/Ubuntu..."
    
    export DEBIAN_FRONTEND=noninteractive
    apt-get update
    apt-get install -y unbound unbound-anchor dns-root-data
    
    UNBOUND_DIR="/etc/unbound"
    UNBOUND_LOG="/var/log/unbound/unbound.log"
    UNBOUND_PID="/run/unbound.pid"
    UNBOUND_CONF="$UNBOUND_DIR/unbound.conf"
    
    mkdir -p /var/log/unbound
    chown unbound:unbound /var/log/unbound
    
    if systemctl is-active --quiet systemd-resolved; then
        warn "systemd-resolved is active. Disabling it..."
        systemctl stop systemd-resolved
        systemctl disable systemd-resolved
        rm -f /etc/resolv.conf
    fi
    
    success "Unbound installed successfully"
}

install_unbound_redhat() {
    log "Installing Unbound on Red Hat/Fedora..."
    
    if command -v dnf &> /dev/null; then
        dnf install -y unbound unbound-libs
    else
        yum install -y unbound unbound-libs
    fi
    
    UNBOUND_DIR="/etc/unbound"
    UNBOUND_LOG="/var/log/unbound.log"
    UNBOUND_PID="/run/unbound.pid"
    UNBOUND_CONF="$UNBOUND_DIR/unbound.conf"
    
    mkdir -p /var/log
    
    success "Unbound installed successfully"
}

install_unbound_arch() {
    log "Installing Unbound on Arch Linux..."
    
    pacman -Sy --noconfirm unbound
    
    UNBOUND_DIR="/etc/unbound"
    UNBOUND_LOG="/var/log/unbound.log"
    UNBOUND_PID="/run/unbound.pid"
    UNBOUND_CONF="$UNBOUND_DIR/unbound.conf"
    
    mkdir -p /var/log
    
    success "Unbound installed successfully"
}

create_unbound_config() {
    log "Creating Unbound configuration..."
    
    if [[ -f "$UNBOUND_CONF" ]]; then
        BACKUP="$UNBOUND_CONF.backup.$(date +%Y%m%d_%H%M%S)"
        log "Backing up existing config to $BACKUP"
        cp "$UNBOUND_CONF" "$BACKUP"
    fi
    
    cat > "$UNBOUND_CONF" << 'EOF'
server:
    verbosity: 1
    interface: 127.0.0.1
    interface: ::1
    port: 53
    
    do-ip4: yes
    do-ip6: yes
    do-udp: yes
    do-tcp: yes
    
    access-control: 127.0.0.0/8 allow
    access-control: ::1 allow
    access-control: 0.0.0.0/0 refuse
    access-control: ::/0 refuse
    
    hide-identity: yes
    hide-version: yes
    harden-glue: yes
    harden-dnssec-stripped: yes
    harden-referral-path: yes
    harden-algo-downgrade: yes
    
    use-caps-for-id: yes
    qname-minimisation: yes
    
    cache-min-ttl: 3600
    cache-max-ttl: 86400
    prefetch: yes
    prefetch-key: yes
    
    serve-expired: yes
    serve-expired-ttl: 86400
    serve-expired-client-timeout: 1800
    
    rrset-cache-size: 100m
    msg-cache-size: 50m
    key-cache-size: 100m
    neg-cache-size: 10m
    
    num-threads: 2
    msg-cache-slabs: 4
    rrset-cache-slabs: 4
    infra-cache-slabs: 4
    key-cache-slabs: 4
    
    outgoing-range: 8192
    num-queries-per-thread: 4096
    so-rcvbuf: 4m
    so-sndbuf: 4m
    
    edns-buffer-size: 1232
    
    unwanted-reply-threshold: 10000
    do-not-query-localhost: no
    
    val-clean-additional: yes
    
    logfile: ""
    use-syslog: yes
    log-queries: no
    log-replies: no

forward-zone:
    name: "."
    
    forward-tls-upstream: yes
    forward-first: no
    
    forward-addr: 1.1.1.1@853#cloudflare-dns.com
    forward-addr: 1.0.0.1@853#cloudflare-dns.com
    
    forward-addr: 9.9.9.9@853#dns.quad9.net
    forward-addr: 149.112.112.112@853#dns.quad9.net
    
    forward-addr: 8.8.8.8@853#dns.google
    forward-addr: 8.8.4.4@853#dns.google
EOF

    success "Configuration created at $UNBOUND_CONF"
}

start_unbound_macos() {
    log "Starting Unbound service on macOS..."
    
    if pgrep -x unbound > /dev/null; then
        log "Stopping existing Unbound process..."
        sudo killall unbound || true
        sleep 2
    fi
    
    brew services start unbound
    
    sleep 3
    
    if pgrep -x unbound > /dev/null; then
        success "Unbound is running"
    else
        error "Failed to start Unbound. Check logs: $UNBOUND_LOG"
    fi
}

start_unbound_linux() {
    log "Starting Unbound service on Linux..."
    
    systemctl daemon-reload
    systemctl enable unbound
    systemctl restart unbound
    
    sleep 3
    
    if systemctl is-active --quiet unbound; then
        success "Unbound is running"
    else
        error "Failed to start Unbound. Check: journalctl -xeu unbound"
    fi
}

configure_system_dns_macos() {
    log "Configuring macOS system DNS..."
    
    INTERFACES=$(networksetup -listallnetworkservices | grep -v "An asterisk" | grep -v "^$")
    
    while IFS= read -r interface; do
        if [[ "$interface" == *"Bluetooth"* ]] || [[ "$interface" == *"Thunderbolt"* ]]; then
            continue
        fi
        
        BACKUP_FILE="$HOME/.unbound_dns_backup_${interface// /_}"
        CURRENT_DNS=$(networksetup -getdnsservers "$interface" 2>/dev/null || echo "")
        
        if [[ -n "$CURRENT_DNS" ]] && [[ "$CURRENT_DNS" != "There aren't any DNS Servers set"* ]]; then
            echo "$CURRENT_DNS" > "$BACKUP_FILE"
            log "Backed up DNS for '$interface' to $BACKUP_FILE"
        fi
        
        log "Setting DNS for '$interface' to 127.0.0.1"
        sudo networksetup -setdnsservers "$interface" 127.0.0.1
    done <<< "$INTERFACES"
    
    sudo dscacheutil -flushcache
    sudo killall -HUP mDNSResponder 2>/dev/null || true
    
    success "System DNS configured to use 127.0.0.1"
}

configure_system_dns_linux() {
    log "Configuring Linux system DNS..."
    
    if [[ -L /etc/resolv.conf ]]; then
        log "Removing symlinked resolv.conf"
        rm -f /etc/resolv.conf
    elif [[ -f /etc/resolv.conf ]]; then
        BACKUP="/etc/resolv.conf.backup.$(date +%Y%m%d_%H%M%S)"
        log "Backing up /etc/resolv.conf to $BACKUP"
        cp /etc/resolv.conf "$BACKUP"
    fi
    
    cat > /etc/resolv.conf << EOF
nameserver 127.0.0.1
options edns0 trust-ad
EOF
    
    chattr +i /etc/resolv.conf 2>/dev/null || true
    
    success "System DNS configured to use 127.0.0.1"
}

test_dns_resolution() {
    log "Testing DNS resolution..."
    
    sleep 2
    
    if command -v dig &> /dev/null; then
        TEST_RESULT=$(dig @127.0.0.1 google.com +short +time=5 2>&1 || echo "FAILED")
        if [[ "$TEST_RESULT" == "FAILED" ]] || [[ -z "$TEST_RESULT" ]]; then
            error "DNS resolution test failed. Check configuration."
        fi
        success "DNS resolution working: $TEST_RESULT"
    elif command -v nslookup &> /dev/null; then
        if nslookup google.com 127.0.0.1 > /dev/null 2>&1; then
            success "DNS resolution working"
        else
            error "DNS resolution test failed"
        fi
    else
        warn "Cannot test DNS (dig/nslookup not found)"
    fi
}

show_completion_message() {
    echo ""
    echo -e "${GREEN}╔══════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║           INSTALLATION COMPLETED SUCCESSFULLY                ║${NC}"
    echo -e "${GREEN}╚══════════════════════════════════════════════════════════════╝${NC}"
    echo ""
    echo -e "${BLUE}Configuration:${NC}"
    echo -e "  Config file: $UNBOUND_CONF"
    echo -e "  Log file: $UNBOUND_LOG"
    echo ""
    echo -e "${BLUE}Useful commands:${NC}"
    
    if [[ "$OS" == "macos" ]]; then
        echo -e "  Check status: ${YELLOW}pgrep -x unbound${NC}"
        echo -e "  View logs: ${YELLOW}tail -f $UNBOUND_LOG${NC}"
        echo -e "  Restart: ${YELLOW}brew services restart unbound${NC}"
        echo -e "  Stop: ${YELLOW}brew services stop unbound${NC}"
        echo -e "  Restore DNS: ${YELLOW}sudo networksetup -setdnsservers Wi-Fi empty${NC}"
    else
        echo -e "  Check status: ${YELLOW}systemctl status unbound${NC}"
        echo -e "  View logs: ${YELLOW}journalctl -xeu unbound${NC}"
        echo -e "  Restart: ${YELLOW}systemctl restart unbound${NC}"
        echo -e "  Stop: ${YELLOW}systemctl stop unbound${NC}"
        echo -e "  Restore DNS: ${YELLOW}sudo chattr -i /etc/resolv.conf && sudo rm /etc/resolv.conf${NC}"
    fi
    
    echo ""
    echo -e "  Test DNS: ${YELLOW}dig @127.0.0.1 google.com${NC}"
    echo ""
    echo -e "${GREEN}Your DNS is now protected with automatic failover!${NC}"
    echo ""
}

main() {
    print_banner
    
    log "Starting Unbound DNS installation..."
    log "Log file: $LOG_FILE"
    
    detect_os
    check_root
    check_port_53
    
    case $OS in
        macos)
            install_unbound_macos
            create_unbound_config
            start_unbound_macos
            configure_system_dns_macos
            ;;
        debian)
            install_unbound_debian
            create_unbound_config
            start_unbound_linux
            configure_system_dns_linux
            ;;
        redhat)
            install_unbound_redhat
            create_unbound_config
            start_unbound_linux
            configure_system_dns_linux
            ;;
        arch)
            install_unbound_arch
            create_unbound_config
            start_unbound_linux
            configure_system_dns_linux
            ;;
    esac
    
    test_dns_resolution
    show_completion_message
}

main "$@"
