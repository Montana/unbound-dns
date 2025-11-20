# unbound-dns

A Fully Independent Recursive DNS Resolver for macOS.
---

This setup ensures your DNS continues working **even if Cloudflare or other upstream DNS providers go offline**, using **full recursive resolution with DNSSEC**.

---

## Why Forwarding Mode Fails

Most default Unbound configurations forward DNS queries directly to Cloudflare:

```bash
forward-zone:
    name: "."
    forward-addr: 1.1.1.1
    forward-addr: 1.0.0.1
```

If Cloudflare fails or blocks requests, **DNS resolution fails entirely**.
To avoid this, we use **recursive mode**, allowing Unbound to resolve domains directly from root DNS servers.

---

## Solution — Full Recursion with DNSSEC

Recursive Unbound becomes its own independent DNS resolver, querying root DNS servers, validating via DNSSEC, and caching locally for speed.

---

## Step 1 — Install Unbound (macOS)

```bash
brew install unbound
```

---

## Step 2 — Download Root DNS Hints

```bash
curl -o /usr/local/etc/unbound/root.hints https://www.internic.net/domain/named.root
```

---

## Step 3 — Enable DNSSEC Trust Anchor

```bash
sudo unbound-anchor
```

---

## Step 4 — Survival Mode Configuration

Create or edit the following file:

```
/usr/local/etc/unbound/unbound.conf
```

Insert:

```bash
server:
    interface: 127.0.0.1
    port: 53
    do-ip4: yes
    do-ip6: no

    root-hints: "/usr/local/etc/unbound/root.hints"
    auto-trust-anchor-file: "/usr/local/etc/unbound/root.key"

    qname-minimisation: yes
    cache-min-ttl: 3600
    cache-max-ttl: 86400
    harden-dnssec-stripped: yes
    hide-identity: yes
    hide-version: yes
    access-control: 127.0.0.0/8 allow
    verbosity: 1
```

---

## Step 5 — Start Unbound

```bash
sudo unbound -d -c /usr/local/etc/unbound/unbound.conf
```

---

## Step 6 — Test Recursive Resolution

```bash
dig google.com @127.0.0.1
```

Expected result should include:

```
;; SERVER: 127.0.0.1#53
```

---

## DNS Latency Testing

```bash
for host in google.com cloudflare.com wikipedia.org github.com; do
  echo "Testing $host"
  time dig "$host" +short >/dev/null
done
```

### Example Results

| Hostname      | Cloudflare Forward-Only | Recursive Unbound |
| ------------- | ----------------------- | ----------------- |
| google.com    | 32ms                    | 44ms              |
| github.com    | 29ms                    | 51ms              |
| wikipedia.org | 30ms                    | 48ms              |

Forwarding mode is usually faster, but recursive mode is fully independent.
Once domains are cached, second lookups often resolve in under **1ms**.

---

## Optional — Matplotlib Chart

`dns_latency_chart.py`:

```python
import matplotlib.pyplot as plt

domains = ["google", "github", "wikipedia", "cloudflare"]
forward = [32, 29, 30, 27]
recursive = [44, 51, 48, 55]

plt.plot(domains, forward, marker='o')
plt.plot(domains, recursive, marker='o')
plt.title("DNS Latency (ms) – Cloudflare Forwarding vs Recursive Unbound")
plt.xlabel("Domain")
plt.ylabel("Latency (ms)")
plt.legend(["Forward Mode", "Recursive Mode"])
plt.savefig("dns_latency_comparison.png")

print("Saved as dns_latency_comparison.png")
```

---

## MITM Hardening (Recommended)

Add to `unbound.conf`:

```bash
server:
    harden-dnssec-stripped: yes
    hide-identity: yes
    hide-version: yes
    harden-glue: yes
    unwanted-reply-threshold: 10000
    do-not-query-localhost: no
    prefetch: yes
    prefetch-key: yes
```

---

## Failover Mode (Recursive First, Cloudflare Only if Needed)

```bash
server:
    root-hints: "/usr/local/etc/unbound/root.hints"
    auto-trust-anchor-file: "/usr/local/etc/unbound/root.key"

forward-zone:
    name: "."
    forward-addr: 1.1.1.1
    forward-addr: 1.0.0.1
    forward-first: yes
```

### Behavior

| Mode       | Priority | When Used          |
| ---------- | -------- | ------------------ |
| Recursive  | Primary  | Always first       |
| Cloudflare | Backup   | If recursion fails |

---

## Failover Mode Test

Block a root server to simulate DNS failure:

```bash
sudo route add -host 198.41.0.4 127.0.0.1
dig google.com @127.0.0.1
```

If configured correctly, Unbound should fall back to Cloudflare and still resolve the query.

---

## Make macOS Use Unbound System-Wide

```bash
networksetup -setdnsservers "Wi-Fi" 127.0.0.1
```

To revert:

```bash
networksetup -setdnsservers "Wi-Fi" Empty
```

---

## Summary

| Feature                 | Status   |
| ----------------------- | -------- |
| Survival Mode           | Active   |
| Failover Mode           | Active   |
| DNSSEC Validation       | Enabled  |
| MITM Hardening          | Added    |
| Recursive Resolution    | Enabled  |
| Automatic macOS Startup | Optional |

---

<img width="1580" height="780" alt="output (27)" src="https://github.com/user-attachments/assets/7d4d13ca-dde1-4248-acd7-c62cefd00450" />


## Author
Michael Mendy (c) 2025.


