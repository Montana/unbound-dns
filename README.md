# unbound-dns

<img width="631" height="800" alt="image" src="https://github.com/user-attachments/assets/25ecd854-1b1d-4bf2-88c7-4b2fdaf79265" />

A resilient local DNS resolver with automatic failover across multiple DNS providers. When Cloudflare goes down, your DNS keeps working. When everything goes down, survival mode kicks in.

## Core Capabilities

This setup provides multi-provider DNS failover with encrypted queries, aggressive caching, and a 24-hour survival mode that serves cached responses even when all upstream providers are unavailable. The system automatically rotates through Cloudflare, Quad9, and Google DNS servers, falling back to cached entries if the internet itself becomes unreachable.

## Requirements

| Component | Requirement |
|-----------|-------------|
| Operating System | macOS (any recent version) |
| Package Manager | Homebrew |
| Privileges | Administrator (sudo) access |
| Network | Active internet connection |

## Installation

Download and run the installer script. It handles everything from Unbound installation to system DNS configuration.

```bash
curl -O https://github.com/montana/unbound-dns.git
chmod +x unbound_dns.sh
./unbound_dns.sh
```
Enter your password when prompted. The script will install Unbound via Homebrew, create an optimized configuration with failover support, start the local DNS resolver on 127.0.0.1:53, configure your system to use it, and verify everything works.

## DNS Provider Hierarchy

The system queries providers in order until one responds. Each provider is queried over encrypted TLS connections.

| Priority | Provider | Primary IP | Secondary IP | Fallback Time |
|----------|----------|------------|--------------|---------------|
| 1st | Cloudflare | 1.1.1.1 | 1.0.0.1 | ~50ms |
| 2nd | Quad9 | 9.9.9.9 | 149.112.112.112 | ~100ms |
| 3rd | Google | 8.8.8.8 | 8.8.4.4 | ~150ms |
| 4th | Survival Mode | Local Cache | Local Cache | Instant |

When all upstream providers fail, survival mode serves cached DNS entries for up to 24 hours. This keeps your already-visited sites accessible during major internet outages.

## System Configuration

| Setting | Location |
|---------|----------|
| Configuration File | `$(brew --prefix)/etc/unbound/unbound.conf` |
| Log File | `$(brew --prefix)/var/log/unbound.log` |
| PID File | `$(brew --prefix)/var/run/unbound.pid` |
| Listen Address | 127.0.0.1:53, ::1:53 |

## Performance Characteristics

| Metric | Value | Impact |
|--------|-------|--------|
| RRset Cache | 100MB | Stores DNS records |
| Message Cache | 50MB | Stores complete responses |
| Worker Threads | 2 | Parallel query processing |
| Cache Hit Rate | 80-90% | After 1 hour of use |
| Stale Cache TTL | 24 hours | Survival mode duration |
| Query Latency (cached) | <1ms | Instant responses |
| Query Latency (upstream) | 10-40ms | Provider dependent |

The aggressive caching strategy means most of your DNS queries resolve instantly from local cache. Popular domains are prefetched before their cache entries expire, maintaining consistently fast performance.

## Architecture Diagram

This is how Unbound works when you run the script:

```bash
╔══════════════════════════════════════════════════════════════╗
║           UNBOUND DNS ARCHITECTURE & FAILOVER                ║
╚══════════════════════════════════════════════════════════════╝

  Your Device (macOS)
        │
        │ DNS Query
        ▼
   ┌─────────────┐
   │   Unbound   │ ◄──── Local Cache (100MB)
   │  127.0.0.1  │       Serves for 24h if upstream fails
   └──────┬──────┘
          │
          │ TLS Encrypted
          │
    ┌─────┴─────┬──────────┬──────────┐
    │           │          │          │
    ▼           ▼          ▼          ▼
┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐
│Cloudfl.│ │Cloudfl.│ │ Quad9  │ │ Quad9  │
│1.1.1.1 │ │1.0.0.1 │ │9.9.9.9 │ │149.112 │
└────────┘ └────────┘ └────────┘ └────────┘
    │           │          │          │
    └───────────┴──────────┴──────────┘
                   │
              If all fail
                   │
                   ▼
         ┌──────────────────┐
         │  Google DNS      │
         │  8.8.8.8         │
         │  8.8.4.4         │
         └──────────────────┘
                   │
              If all fail
                   │
                   ▼
         ┌──────────────────┐
         │  SURVIVAL MODE   │
         │  Serve Cache     │
         │  (up to 24h)     │
         └──────────────────┘
```

Your DNS keeps working even when providers go down. That's the whole point.

## Service Management Commands

| Task | Command |
|------|---------|
| Check if running | `pgrep -x unbound` |
| View live logs | `tail -f $(brew --prefix)/var/log/unbound.log` |
| Restart service | `sudo killall unbound && sudo unbound -d -c $(brew --prefix)/etc/unbound/unbound.conf &` |
| Stop service | `sudo killall unbound` |
| Test resolution | `dig @127.0.0.1 google.com` |
| Restore system DNS | `sudo networksetup -setdnsservers "Wi-Fi" empty` |

## Troubleshooting Guide

### DNS Not Working

| Step | Command | What It Checks |
|------|---------|----------------|
| 1. Verify process | `pgrep -x unbound` | Is Unbound running? |
| 2. Check logs | `cat $(brew --prefix)/var/log/unbound.log` | Any error messages? |
| 3. Validate config | `unbound-checkconf $(brew --prefix)/etc/unbound/unbound.conf` | Configuration syntax |
| 4. Test upstream | `dig @1.1.1.1 google.com` | Can reach providers? |

### Port Conflict Resolution

If port 53 is already in use, identify the conflicting process and stop it:

```bash
sudo lsof -i :53
sudo killall -9 [process_name]
```

### Performance Issues

| Symptom | Diagnostic Command | Solution |
|---------|-------------------|----------|
| Slow queries | `dig @127.0.0.1 google.com +stats` | Check upstream latency |
| Cache thrashing | View logs for high miss rate | Increase cache size |
| High CPU usage | `top -pid $(pgrep unbound)` | Reduce threads or cache |

Clear the cache with `sudo killall -HUP unbound` to force fresh queries.

## Security & Privacy Features

| Feature | Implementation | Benefit |
|---------|----------------|---------|
| Encryption | DNS-over-TLS (port 853) | ISP can't see queries |
| DNSSEC | Cryptographic validation | Prevents DNS spoofing |
| Query Minimization | RFC 7816 compliance | Reduces information leakage |
| No Logging | Disabled by default | No local query history |
| Identity Hiding | Stripped resolver info | Anonymizes requests |
| Access Control | Localhost only | Prevents external abuse |

## Advanced Configuration

### Enabling Local Network Access

To allow other devices on your network to use your Unbound instance, modify `unbound.conf`:

```
interface: 0.0.0.0
access-control: 10.0.0.0/8 allow
access-control: 192.168.0.0/16 allow
access-control: 172.16.0.0/12 allow
```

### Cache Tuning

| Parameter | Default | High Performance | Low Memory |
|-----------|---------|------------------|------------|
| rrset-cache-size | 100m | 256m | 50m |
| msg-cache-size | 50m | 128m | 25m |
| num-threads | 2 | 4 | 1 |

### Custom DNS Providers

Edit the `forward-zone` section to use different providers. For example, to add OpenDNS:

```
forward-addr: 208.67.222.222@853#dns.opendns.com
forward-addr: 208.67.220.220@853#dns.opendns.com
```

### Query Logging

Enable detailed logging for debugging purposes:

```
log-queries: yes
log-replies: yes
log-local-actions: yes
```

Note: This significantly increases log file size and may impact privacy.

## Complete Uninstallation

| Step | Command | Purpose |
|------|---------|---------|
| 1. Restore DNS | `sudo networksetup -setdnsservers "Wi-Fi" empty` | Use system default |
| 2. Stop service | `sudo killall unbound` | Terminate process |
| 3. Remove package | `brew uninstall unbound` | Delete binary |
| 4. Clean config | `rm -rf $(brew --prefix)/etc/unbound` | Remove settings |

## Why This Matters

Standard DNS configurations use a single provider. When that provider experiences an outage, your entire internet connection becomes unusable, even though your network connection is fine. This setup provides true redundancy with automatic failover and a survival mode that keeps you online using cached entries when the entire DNS infrastructure fails.

The encrypted DNS-over-TLS prevents your ISP from logging every website you visit. Query minimization reduces the amount of information leaked to DNS servers. DNSSEC validation prevents attackers from redirecting you to malicious sites through DNS poisoning.

<img width="1580" height="780" alt="output (27)" src="https://github.com/user-attachments/assets/7d4d13ca-dde1-4248-acd7-c62cefd00450" />

Local caching means faster page loads since most DNS queries resolve instantly without network round trips. Prefetching keeps popular domains fresh in cache. The result is a faster, more private, and more resilient internet connection.


## Author

Michael Mendy (c) 2025.
