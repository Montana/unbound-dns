#!/usr/bin/env bash
set -euo pipefail

if ! command -v brew >/dev/null 2>&1; then
  echo "Homebrew is not installed. Install it from https://brew.sh first."
  exit 1
fi

BREW_PREFIX="$(brew --prefix)"
UNBOUND_ETC="${BREW_PREFIX}/etc/unbound"
UNBOUND_CONF="${UNBOUND_ETC}/unbound.conf"

brew install unbound

mkdir -p "${UNBOUND_ETC}"

if [ -f "${UNBOUND_CONF}" ]; then
  cp "${UNBOUND_CONF}" "${UNBOUND_CONF}.bak"
fi

cat > "${UNBOUND_CONF}" <<'EOF'
server:
    verbosity: 1
    interface: 0.0.0.0
    interface: 127.0.0.1
    port: 53
    do-ip4: yes
    do-ip6: no
    username: ""
    chroot: ""
    directory: "/"
    logfile: ""
    pidfile: "/usr/local/var/run/unbound.pid"
    qname-minimisation: yes
    hide-identity: yes
    hide-version: yes
    harden-glue: yes
    harden-dnssec-stripped: yes
    prefetch: yes
    access-control: 127.0.0.0/8 allow
    access-control: 10.0.0.0/8 allow
    access-control: 192.168.0.0/16 allow
forward-zone:
    name: "."
    forward-addr: 1.1.1.1
    forward-addr: 1.0.0.1
    forward-addr: 8.8.8.8
    forward-addr: 8.8.4.4
EOF

unbound-checkconf "${UNBOUND_CONF}"

if pgrep -x unbound >/dev/null 2>&1; then
  sudo killall unbound || true
fi

sudo unbound -d -c "${UNBOUND_CONF}" >/tmp/unbound.log 2>&1 &

sleep 2

if pgrep -x unbound >/dev/null 2>&1; then
  echo "Unbound appears to be running."
else
  echo "ERROR: Unbound did not start correctly. Check /tmp/unbound.log"
  exit 1
fi

PRIMARY_SERVICE="$(networksetup -listallnetworkservices 2>/dev/null | sed '1d' | head -n1 || true)"

if [ -z "${PRIMARY_SERVICE}" ]; then
  echo "WARNING: Could not determine primary network service automatically."
  echo "You may need to run: sudo networksetup -setdnsservers 'Wi-Fi' 127.0.0.1"
else
  sudo networksetup -setdnsservers "${PRIMARY_SERVICE}" 127.0.0.1
fi

if command -v dig >/dev/null 2>&1; then
  dig @127.0.0.1 google.com +short || true
else
  echo "Note: 'dig' not found. You can install it with: brew install bind"
fi
