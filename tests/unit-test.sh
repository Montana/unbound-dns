#!/usr/bin/env bash

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m'

PASSED=0
FAILED=0

test_readme_exists() {
    if [ -f "$PROJECT_ROOT/README.md" ]; then
        echo -e "${GREEN}✓${NC} README.md exists"
        ((PASSED++))
    else
        echo -e "${RED}✗${NC} README.md missing"
        ((FAILED++))
    fi
}

test_installation_script_exists() {
    if [ -f "$PROJECT_ROOT/unbound_dns.sh" ]; then
        echo -e "${GREEN}✓${NC} unbound_dns.sh exists"
        ((PASSED++))
    else
        echo -e "${RED}✗${NC} unbound_dns.sh missing"
        ((FAILED++))
    fi
}

test_script_is_executable() {
    if [ -x "$PROJECT_ROOT/unbound_dns.sh" ]; then
        echo -e "${GREEN}✓${NC} unbound_dns.sh is executable"
        ((PASSED++))
    else
        echo -e "${RED}✗${NC} unbound_dns.sh is not executable"
        ((FAILED++))
    fi
}

test_script_has_shebang() {
    if head -n1 "$PROJECT_ROOT/unbound_dns.sh" | grep -q "^#!"; then
        echo -e "${GREEN}✓${NC} Script has shebang"
        ((PASSED++))
    else
        echo -e "${RED}✗${NC} Script missing shebang"
        ((FAILED++))
    fi
}

test_readme_has_content() {
    local word_count=$(wc -w < "$PROJECT_ROOT/README.md" | tr -d ' ')
    if [ "$word_count" -gt 100 ]; then
        echo -e "${GREEN}✓${NC} README has substantial content ($word_count words)"
        ((PASSED++))
    else
        echo -e "${RED}✗${NC} README too short ($word_count words)"
        ((FAILED++))
    fi
}

echo "Running Unit Tests..."
echo "===================="
echo ""

test_readme_exists
test_installation_script_exists
test_script_is_executable
test_script_has_shebang
test_readme_has_content

echo ""
echo "===================="
echo "Results: $PASSED passed, $FAILED failed"
echo "===================="

if [ $FAILED -gt 0 ]; then
    exit 1
else
    exit 0
fi
