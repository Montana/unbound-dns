#!/usr/bin/env bash

set -e

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

PASSED=0
FAILED=0
SKIPPED=0

test_dns_provider() {
    local provider=$1
    local name=$2
    
    if ! command -v dig &> /dev/null; then
        echo -e "${YELLOW}⊘${NC} DNS test skipped (dig not available)"
        ((SKIPPED++))
        return
    fi
    
    if timeout 5 dig @"$provider" google.com +short +time=3 &> /dev/null; then
        echo -e "${GREEN}✓${NC} $name ($provider) is reachable"
        ((PASSED++))
    else
        echo -e "${RED}✗${NC} $name ($provider) unreachable"
        ((FAILED++))
    fi
}

test_dns_over_tls() {
    if ! command -v openssl &> /dev/null; then
        echo -e "${YELLOW}⊘${NC} DNS-over-TLS test skipped (openssl not available)"
        ((SKIPPED++))
        return
    fi
    
    if timeout 5 openssl s_client -connect 1.1.1.1:853 -servername cloudflare-dns.com </dev/null 2>&1 | grep -q "Verify return code: 0"; then
        echo -e "${GREEN}✓${NC} DNS-over-TLS connection successful"
        ((PASSED++))
    else
        echo -e "${RED}✗${NC} DNS-over-TLS connection failed"
        ((FAILED++))
    fi
}

echo "Running Integration Tests..."
echo "============================"
echo ""

test_dns_provider "1.1.1.1" "Cloudflare"
test_dns_provider "9.9.9.9" "Quad9"
test_dns_provider "8.8.8.8" "Google DNS"
test_dns_over_tls

echo ""
echo "============================"
echo "Results: $PASSED passed, $FAILED failed, $SKIPPED skipped"
echo "============================"

if [ $FAILED -gt 0 ]; then
    exit 1
else
    exit 0
fi
