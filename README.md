[![CI](https://github.com/Montana/unbound-dns/actions/workflows/ci.yml/badge.svg)](https://github.com/Montana/unbound-dns/actions/workflows/ci.yml) [![Build Status](https://app.travis-ci.com/Montana/unbound-dns.svg?token=U865GtC2ptqX3Ezf3Fzb&branch=master)](https://app.travis-ci.com/Montana/unbound-dns)

# unbound-dns

Unbound knows exactly who to call when Cloudflare doesn't pick up.

<img width="469" height="469" alt="political pressures (3)" src="https://github.com/user-attachments/assets/6e9da7c6-9ace-4e2a-bc93-6d7fb783f02c" />

Unbound DNS runs on your local machine as a local DNS resolver, translating domain names to IP addresses while caching responses for speed, encrypting queries for privacy, and automatically switching between DNS providers when one fails.

<img width="631" height="800" alt="image" src="https://github.com/user-attachments/assets/25ecd854-1b1d-4bf2-88c7-4b2fdaf79265" />

A resilient local DNS resolver with automatic failover across multiple DNS providers. When Cloudflare goes down, your DNS keeps working. When everything goes down, survival mode kicks in.

## System Requirements

Before you get started here are the system requirements you'll need in order to run my script: 

## System Requirements

| Component        | Requirement                                      |
|------------------|--------------------------------------------------|
| macOS            | Any recent version with Homebrew                 |
| Ubuntu/Debian    | 20.04+                                           |
| Fedora/RHEL/CentOS | 8+                                             |
| Arch Linux       | Latest                                           |
| Windows          | Windows 10/11 or Server 2016+                    |
| Privileges       | Administrator (sudo) access                      |
| Network          | Active internet connection                       |


## Windows Requirements 

Windows is a bit different, in particular if you're running it in WSL2, or hypothetically even WSL.

| Component | Requirement |
|---|---|
| Operating System | Windows 10/11 or Windows Server 2016+ |
| PowerShell | Version 5.1 or higher |
| Privileges | Administrator access |
| Network | Active internet connection |
| .NET Framework | 4.7.2 or higher |

>PAN (Palo Alto Networks) capabilities are in the works as well. 

## Core Capabilities

This setup provides multi-provider DNS failover with encrypted queries, aggressive caching, and a 24-hour survival mode that serves cached responses even when all upstream providers are unavailable. The system automatically rotates through Cloudflare, Quad9, and Google DNS servers, falling back to cached entries if the internet itself becomes unreachable.

## Verifying Unbound is Actually Working

After installation, you need to confirm that Unbound isn't just running as a background process, but is actually handling your DNS queries. Here's how to verify everything is working correctly.

### Basic Functionality Test

The simplest way to check if Unbound is responding to queries is to ask it directly to resolve a domain name. On macOS or Linux, use `dig @127.0.0.1 google.com`, or on Windows, use `Resolve-DnsName -Name google.com -Server 127.0.0.1`. You should get back a valid IP address with a query time under 50ms on the first try, and under 1ms on subsequent queries due to caching.

But this only proves Unbound can answer questions when you ask it directly. Your system might still be bypassing it entirely and using your ISP's DNS servers. To check what your system is actually using, run `scutil --dns | grep "nameserver"` on macOS, `cat /etc/resolv.conf` on Linux, or `Get-DnsClientServerAddress -AddressFamily IPv4` on Windows. You should see 127.0.0.1 listed as your primary nameserver. If you see something else like 8.8.8.8 or your router's IP, then your system isn't using Unbound at all.

### Proving the Cache Works

The whole point of running a local DNS resolver is caching, so you should verify that's actually happening. Run a DNS query for a domain you haven't visited recently and note the response time. Then immediately run the same query again. The second query should be dramatically faster—we're talking sub-millisecond response times versus 20-50ms for the first query. On macOS/Linux you can use `time dig @127.0.0.1 example.com | grep "Query time"` to see the timing clearly. On Windows, wrap your Resolve-DnsName command in `Measure-Command { }` to see how long it takes.

If both queries take roughly the same amount of time, something is wrong. Either Unbound isn't caching properly, or your queries aren't actually going through Unbound at all. Check the logs to see what's happening. On macOS, the logs are at `$(brew --prefix)/var/log/unbound.log`, on Linux they're typically in `/var/log/unbound/`, and on Windows you'll find them at `C:\Program Files\Unbound\unbound.log`.

### Testing Encrypted Queries

One of the major benefits of this setup is that your DNS queries are encrypted via DNS-over-TLS. To verify this is actually happening, you need to look at network traffic. Install tcpdump on macOS/Linux and run `sudo tcpdump -i any port 53 or port 853 -n` while making DNS queries in another terminal. You should see connections to port 853 (the TLS port) going to upstream providers like 1.1.1.1, but you should NOT see unencrypted port 53 traffic going to external IPs. The only port 53 traffic should be between your system and 127.0.0.1 (localhost).

On Windows, you can use `netstat -an | Select-String "853"` to see active connections to port 853, or open Resource Monitor (resmon.exe) and check the Network tab. If you don't see any port 853 connections when making DNS queries, then encryption isn't working and you're probably falling back to unencrypted DNS somehow.

### Verifying Failover Works

The failover mechanism is critical—if Cloudflare goes down, you want Unbound to seamlessly switch to Quad9 or Google DNS. To test this, you can temporarily block Cloudflare's IPs and verify that DNS still works. On macOS/Linux, add firewall rules with `sudo iptables -A OUTPUT -d 1.1.1.1 -j DROP` and `sudo iptables -A OUTPUT -d 1.0.0.1 -j DROP`. On Windows, create a firewall rule with `New-NetFirewallRule -DisplayName "Block Cloudflare Test" -Direction Outbound -RemoteAddress 1.1.1.1,1.0.0.1 -Action Block`.

Now try resolving a domain you haven't queried recently (so it's not in cache). The query should still succeed, though it might take slightly longer as Unbound fails over to the next provider in the list. You can check the logs to see which upstream server responded. When you're done testing, remove the firewall rules with `sudo iptables -D OUTPUT -d 1.1.1.1 -j DROP` on Linux or `Remove-NetFirewallRule -DisplayName "Block Cloudflare Test"` on Windows.

### Testing DNSSEC Validation

DNSSEC prevents attackers from poisoning DNS responses and redirecting you to malicious sites. To verify it's working, try querying a domain with intentionally broken DNSSEC: `dig @127.0.0.1 dnssec-failed.org` or `Resolve-DnsName -Name dnssec-failed.org -Server 127.0.0.1`. This query should fail with a SERVFAIL error, which proves DNSSEC validation is active. If the query succeeds, DNSSEC validation isn't working and you're vulnerable to DNS spoofing attacks.

You can also verify DNSSEC is working on legitimate domains by querying with the DNSSEC flag: `dig @127.0.0.1 cloudflare.com +dnssec`. Look for RRSIG records in the response and an "ad" (authenticated data) flag.

### Monitoring Real Activity

To really understand what Unbound is doing, watch the logs in real-time while browsing the web. Use `tail -f $(brew --prefix)/var/log/unbound.log` on macOS, `sudo tail -f /var/log/unbound/unbound.log` on Linux, or `Get-Content "C:\Program Files\Unbound\unbound.log" -Wait -Tail 20` on Windows. Then open a web browser and visit a few sites. You should see queries flowing through, cache hits being served instantly, and upstream server connections when new domains are requested.

If you don't see any activity in the logs while browsing, your system is definitely not using Unbound. Go back and check your DNS configuration. If you see queries but they're all going upstream without any cache hits, your cache settings might be misconfigured or too small.

### Testing Survival Mode

The 24-hour survival mode is supposed to keep serving cached DNS responses even when all upstream providers are unreachable. To test this, first query a domain like `dig @127.0.0.1 github.com` to get it into cache. Then simulate a complete internet outage by blocking all outbound DNS traffic. On macOS/Linux, use `sudo iptables -A OUTPUT -p tcp --dport 853 -j DROP` and `sudo iptables -A OUTPUT -p udp --dport 53 -j DROP`. On Windows, you can disable all network adapters except loopback with `Get-NetAdapter | Where-Object {$_.Name -ne "Loopback"} | Disable-NetAdapter -Confirm:$false`.

<img width="1180" height="780" alt="output (28)" src="https://github.com/user-attachments/assets/7a4366c0-5aff-4368-b6df-a091ed4643d3" />

>The graph illustrates how Unbound’s survival mode performs during a complete internet outage. As soon as outbound DNS traffic is blocked, the resolver begins relying solely on its cache. At the beginning of the outage, very few domains resolve successfully because the cache hasn’t yet accumulated much data. Over time, as more domains have been queried before the outage, the number of cached responses that Unbound can still serve begins to rise. 

Now try querying github.com again. Even though there's no internet connection, Unbound should still return the cached IP address. This is survival mode in action. New domains that aren't cached will fail, but anything you've visited recently should still resolve. Clean up your test by removing the firewall rules or re-enabling network adapters when you're done.

## Graphical User Interface

To use the Unbound DNS Installer GUI, first ensure both files (`unbound_gui.py` and `unbound_install.sh`) are in the same directory. Launch the application by opening a terminal, navigating to the directory containing the files, and running python3 unbound_gui.py. The interface will open showing a clean window with status information at the top, a large output section in the middle, and control buttons at the bottom.

When you're ready to install Unbound DNS for the first time, simply click the Install button. The system will prompt you to confirm the installation and warn you that it requires sudo privileges. After confirming, you'll be asked to enter your system password. The installation process will begin and you'll see detailed progress in the output window as the script detects your operating system, checks for conflicts, installs Unbound, creates the configuration file, starts the service, and configures your system DNS settings. 

This process typically takes between one to five minutes depending on your system and internet connection. Watch the output window for green success messages indicating each step has completed. When installation finishes, you'll see a completion message and the status section will update to show Unbound as running. 

## GUI Management Commands

<img width="888" height="721" alt="Screenshot 2025-11-21 at 1 36 04 PM" src="https://github.com/user-attachments/assets/bcb9e7cd-2aac-4008-970c-e7885babffdf" />

<br> While the GUI provides all the controls you need, you can also manage Unbound from the command line if preferred. On macOS, use brew services status unbound to check status, brew services restart unbound to restart the service, and brew services stop unbound to stop it. On Linux systems, use `systemctl status unbound` to check status, systemctl restart unbound to restart, and systemctl stop unbound to stop the service. To view detailed logs on macOS, run `tail -f $(brew --prefix)/var/log/unbound.log`, and on Linux use `journalctl -xeu unbound`. For testing DNS resolution, use `dig @127.0.0.1 google.com` which queries your local Unbound server and displays the results. </br>

### Comparing with Direct DNS Queries

As a sanity check, you can compare Unbound's responses with what you'd get from querying an upstream provider directly. Query a domain through Unbound with `dig @127.0.0.1 amazon.com`, then query the same domain directly through Cloudflare with `dig @1.1.1.1 amazon.com`. The IP addresses returned should match (they might be in different order, but the same IPs should appear). If you get completely different results, either Unbound is serving very stale cache data or something is seriously misconfigured.

### Performance Reality Check

To get a sense of real-world performance, test a variety of domains under different conditions. Query five or ten popular domains you haven't visited recently and note the response times. These first queries will be cache misses and require upstream lookups, so they might take 20-50ms depending on the upstream provider's latency. Then immediately query the same domains again. The second round should be nearly instant—under 1ms for cached responses.

If your cached queries are still taking 10-20ms, something is interfering with the cache. Check that your cache size settings in the configuration file are adequate (should be at least 50MB for the message cache and 100MB for the RRset cache). If first queries are consistently slow (over 100ms), you might be experiencing failover delays or network issues reaching the upstream providers. Check that port 853 isn't being blocked by your firewall or ISP.

<img width="891" height="1098" alt="Screenshot 2025-11-20 at 8 47 47 PM" src="https://github.com/user-attachments/assets/8aa3f4e6-a0ef-4ad6-b295-bc7663b5ba78" />

The difference between cached and uncached queries should be dramatic. If it's not, Unbound isn't providing much value and you should investigate why caching isn't working properly.

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
curl -O https://raw.githubusercontent.com/Montana/unbound-dns/main/unbound_dns.sh
chmod +x unbound_dns.sh
./unbound_dns.sh
```
If you want to use this in Windows please do the following: 

### Windows

```bash
git clone https://github.com/Montana/unbound-dns.git
cd unbound-dns
Set-ExecutionPolicy Bypass -Scope Process
.\install_windows.ps1
```

Enter your password when prompted on Windows or macOS (even WSL2), the script will install Unbound via Homebrew, create an optimized configuration with failover support, start the local DNS resolver on 127.0.0.1:53, configure your system to use it, and verify everything works.

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

## Windows System Configuration Files

| Component | Location |
|-----------|----------|
| Configuration File | `C:\Program Files\Unbound\service.conf` |
| Log File | `C:\Program Files\Unbound\unbound.log` |
| Executable | `C:\Program Files\Unbound\unbound.exe` |
| DNS Backup | `%USERPROFILE%\.unbound_dns_backup.json` |

## Linux System Configuration Files

| Setting | Location |
|--------|----------|
| Config | `/etc/unbound/unbound.conf` |
| Log | `/var/log/unbound/unbound.log` (RHEL/Arch) / `/var/log/unbound/unbound.log` (Debian) |
| PID | `/run/unbound.pid` |

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

## MacOS Management Commands

| Task | Command |
|------|---------|
| Check if running | `pgrep -x unbound` |
| View live logs | `tail -f $(brew --prefix)/var/log/unbound.log` |
| Restart service | `sudo killall unbound && sudo unbound -d -c $(brew --prefix)/etc/unbound/unbound.conf &` |
| Stop service | `sudo killall unbound` |
| Test resolution | `dig @127.0.0.1 google.com` |
| Restore system DNS | `sudo networksetup -setdnsservers "Wi-Fi" empty` |

## Linux Management Commands

| Task         | Command                                                                 |
|--------------|-------------------------------------------------------------------------|
| Check status | `systemctl status unbound`                                              |
| View logs    | `journalctl -xeu unbound`                                               |
| Restart      | `sudo systemctl restart unbound`                                        |
| Stop         | `sudo systemctl stop unbound`                                           |
| Test DNS     | `dig @127.0.0.1 google.com`                                             |
| Restore DNS  | `sudo chattr -i /etc/resolv.conf && sudo rm /etc/resolv.conf`           |

## Windows Management Commands

| Task         | Command                                                                 |
|--------------|-------------------------------------------------------------------------|
| Check status | `Get-Service unbound`                                                   |
| View logs    | `Get-Content "C:\Program Files\Unbound\unbound.log" -Tail 50`           |
| Restart      | `Restart-Service unbound`                                               |
| Stop         | `Stop-Service unbound`                                                  |
| Test DNS     | `Resolve-DnsName google.com -Server 127.0.0.1`                          |
| Restore DNS  | `Get-NetAdapter \| Set-DnsClientServerAddress -ResetServerAddresses`    |


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
