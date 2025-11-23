#!/usr/bin/env bash

set -e

backup_resolv="/etc/resolv.conf.unbound-dns.bak"

if [ "$EUID" -ne 0 ]; then
  echo "Run as root (sudo)"
  exit 1
fi

os="$(uname -s)"

if [ -f "$backup_resolv" ]; then
  chattr -i /etc/resolv.conf 2>/dev/null || true
  rm -f /etc/resolv.conf
  mv "$backup_resolv" /etc/resolv.conf
  echo "Restored resolv.conf"
else
  echo "No backup resolv.conf found"
fi

if [ "$os" = "Darwin" ]; then
  if command -v brew >/dev/null 2>&1; then
    brew services stop unbound 2>/dev/null || true
    brew uninstall unbound 2>/dev/null || true
  fi
else
  if command -v systemctl >/dev/null 2>&1; then
    systemctl stop unbound 2>/dev/null || true
    systemctl disable unbound 2>/dev/null || true
  fi

  if command -v apt-get >/dev/null 2>&1; then
    apt-get remove -y unbound 2>/dev/null || true
    apt-get purge -y unbound 2>/dev/null || true
  elif command -v dnf >/dev/null 2>&1; then
    dnf remove -y unbound 2>/dev/null || true
  elif command -v yum >/dev/null 2>&1; then
    yum remove -y unbound 2>/dev/null || true
  elif command -v pacman >/dev/null 2>&1; then
    pacman -Rns --noconfirm unbound 2>/dev/null || true
  fi
fi

rm -rf /etc/unbound 2>/dev/null || true
rm -rf /var/log/unbound 2>/dev/null || true

if command -v brew >/dev/null 2>&1; then
  prefix="$(brew --prefix)"
  rm -rf "$prefix/etc/unbound" 2>/dev/null || true
  rm -rf "$prefix/var/log/unbound.log" 2>/dev/null || true
fi

echo "Unbound DNS uninstalled"
echo "Verify DNS manually if needed"
