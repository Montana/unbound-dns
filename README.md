# unbound-dns

<img width="631" height="800" alt="image" src="https://github.com/user-attachments/assets/25ecd854-1b1d-4bf2-88c7-4b2fdaf79265" />


# Unbound DNS Setup for macOS

A resilient local DNS resolver with automatic failover across multiple DNS providers.

## Features

- **Multi-Provider Failover**: Cloudflare → Quad9 → Google DNS
- **Survival Mode**: Serves cached responses even when all upstream providers are down
- **DNS-over-TLS**: Encrypted DNS queries for privacy
- **Performance Optimized**: Caching, prefetching, and thread tuning
- **Privacy Focused**: Query minimization, identity hiding, DNSSEC hardening
- **Automatic Backup**: Timestamped backups of existing configurations

## Requirements

- macOS
- Homebrew package manager
- Administrator privileges (sudo access)

## Installation

1. Download the script:
```bash
curl -O https://github.com/montana/unbound-dns.git
chmod +x unbound_dns.sh
```

2. Run the installer:
```bash
./unbound_dns.sh
```

3. Enter your password when prompted for sudo access

## What It Does

1. Installs Unbound via Homebrew
2. Creates optimized configuration with failover support
3. Starts Unbound as a local DNS resolver on 127.0.0.1:53
4. Configures your system to use the local resolver
5. Tests DNS resolution

## Failover Strategy

### Primary: Cloudflare DNS
- 1.1.1.1
- 1.0.0.1

### Secondary: Quad9 DNS
- 9.9.9.9
- 149.112.112.112

### Tertiary: Google DNS
- 8.8.8.8
- 8.8.4.4

### Survival Mode
When all providers are unavailable, Unbound serves cached DNS responses for up to 24 hours, keeping your internet functional during outages.

## Configuration

Config location: `$(brew --prefix)/etc/unbound/unbound.conf`

Log location: `$(brew --prefix)/var/log/unbound.log`

### Key Settings

- **Cache Size**: 100MB RRset cache, 50MB message cache
- **Cache Duration**: Expired entries served for 24 hours during outages
- **Threads**: 2 worker threads
- **Security**: DNSSEC validation, query minimization
- **Privacy**: DNS-over-TLS, no query logging

## Flowchart

This is the antaomy of Unbound and how it would work if you run my script: 

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
It is worth noting your DNS keeps working even when providers go down, which is kind of the whole point. 

## Management

### Check Status
```bash
pgrep -x unbound
```

### View Logs
```bash
tail -f $(brew --prefix)/var/log/unbound.log
```

### Restart Service
```bash
sudo killall unbound
sudo unbound -d -c $(brew --prefix)/etc/unbound/unbound.conf &
```

### Stop Service
```bash
sudo killall unbound
```

### Test DNS Resolution
```bash
dig @127.0.0.1 google.com
```

### Restore Previous DNS Settings
```bash
sudo networksetup -setdnsservers "Wi-Fi" empty
```

## Troubleshooting

### DNS Not Working

Check if Unbound is running:
```bash
pgrep -x unbound
```

Check logs for errors:
```bash
cat $(brew --prefix)/var/log/unbound.log
```

Validate configuration:
```bash
unbound-checkconf $(brew --prefix)/etc/unbound/unbound.conf
```

### Port 53 Already in Use

Check what's using port 53:
```bash
sudo lsof -i :53
```

Stop conflicting service or change Unbound port in config.

### Slow DNS Resolution

Check upstream connectivity:
```bash
dig @1.1.1.1 google.com
dig @9.9.9.9 google.com
dig @8.8.8.8 google.com
```

Clear cache:
```bash
sudo killall -HUP unbound
```

## Customization

### Allow Local Network Access

Uncomment these lines in `unbound.conf`:
```
access-control: 10.0.0.0/8 allow
access-control: 192.168.0.0/16 allow
access-control: 172.16.0.0/12 allow
```

Then change interface binding:
```
interface: 0.0.0.0
```

### Change DNS Providers

Edit the `forward-zone` section in `unbound.conf` to add/remove providers.

### Adjust Cache Size

Modify these values:
```
rrset-cache-size: 100m
msg-cache-size: 50m
```

### Enable Query Logging

Set in `unbound.conf`:
```
log-queries: yes
log-replies: yes
```

## Uninstall

1. Restore original DNS settings:
```bash
sudo networksetup -setdnsservers "Wi-Fi" empty
```

2. Stop Unbound:
```bash
sudo killall unbound
```

3. Remove Unbound:
```bash
brew uninstall unbound
```

4. Remove configuration (optional):
```bash
rm -rf $(brew --prefix)/etc/unbound
```

## Performance Benefits

- **Faster Lookups**: Local caching eliminates repeated queries
- **Reduced Latency**: No round-trip to external DNS servers for cached entries
- **Prefetching**: Popular domains refreshed before expiration
- **Outage Protection**: Serves stale cache during provider failures

## Privacy Benefits

- **Encrypted Queries**: DNS-over-TLS prevents ISP snooping
- **Query Minimization**: Only sends necessary information to DNS servers
- **No Logging**: Your queries aren't stored locally
- **Identity Hidden**: DNS server can't identify your resolver

## Security Features

- **DNSSEC Validation**: Cryptographic verification of DNS responses
- **Hardened Configuration**: Protection against various DNS attacks
- **Strict TLS**: Only uses encrypted connections to upstream servers
- **Access Control**: Only localhost can query by default

<img width="1580" height="780" alt="output (27)" src="https://github.com/user-attachments/assets/7d4d13ca-dde1-4248-acd7-c62cefd00450" />

## Author
Michael Mendy (c) 2025.


