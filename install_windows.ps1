param(
    [switch]$Uninstall,
    [switch]$DryRun
)

function Test-AdminPrivileges {
    $currentPrincipal = New-Object Security.Principal.WindowsPrincipal([Security.Principal.WindowsIdentity]::GetCurrent())
    $isAdmin = $currentPrincipal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
    
    if (-not $isAdmin) {
        Write-Error "This script requires Administrator privileges. Please run PowerShell as Administrator."
        exit 1
    }
    
    Write-Host "✓ Running with Administrator privileges" -ForegroundColor Green
}

function Install-Unbound {
    Write-Host "`nInstalling Unbound DNS Resolver..." -ForegroundColor Cyan
    
    if (-not (Get-Command choco -ErrorAction SilentlyContinue)) {
        Write-Host "Chocolatey not found. Installing Chocolatey..." -ForegroundColor Yellow
        Set-ExecutionPolicy Bypass -Scope Process -Force
        [System.Net.ServicePointManager]::SecurityProtocol = [System.Net.ServicePointManager]::SecurityProtocol -bor 3072
        Invoke-Expression ((New-Object System.Net.WebClient).DownloadString('https://community.chocolatey.org/install.ps1'))
    }
    
    if ($DryRun) {
        Write-Host "[DRY RUN] Would install: choco install unbound -y" -ForegroundColor Yellow
        return
    }
    
    choco install unbound -y
    
    if ($LASTEXITCODE -ne 0) {
        Write-Error "Failed to install Unbound"
        exit 1
    }
    
    Write-Host "✓ Unbound installed successfully" -ForegroundColor Green
    
    $configPath = "C:\Program Files\Unbound\service.conf"
    $configDir = Split-Path $configPath
    
    if (-not (Test-Path $configDir)) {
        New-Item -ItemType Directory -Path $configDir -Force | Out-Null
    }
    
    $config = @"
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
    
    hide-identity: yes
    hide-version: yes
    harden-glue: yes
    harden-dnssec-stripped: yes
    use-caps-for-id: yes
    
    cache-min-ttl: 3600
    cache-max-ttl: 86400
    prefetch: yes
    prefetch-key: yes
    
    rrset-cache-size: 100m
    msg-cache-size: 50m
    num-threads: 2
    
    serve-expired: yes
    serve-expired-ttl: 86400
    
    qname-minimisation: yes
    
    logfile: "C:\Program Files\Unbound\unbound.log"
    log-queries: no
    log-replies: no

forward-zone:
    name: "."
    forward-tls-upstream: yes
    
    forward-addr: 1.1.1.1@853#cloudflare-dns.com
    forward-addr: 1.0.0.1@853#cloudflare-dns.com
    
    forward-addr: 9.9.9.9@853#dns.quad9.net
    forward-addr: 149.112.112.112@853#dns.quad9.net
    
    forward-addr: 8.8.8.8@853#dns.google
    forward-addr: 8.8.4.4@853#dns.google
"@
    
    if ($DryRun) {
        Write-Host "[DRY RUN] Would create config at: $configPath" -ForegroundColor Yellow
        Write-Host $config -ForegroundColor Gray
        return
    }
    
    $config | Out-File -FilePath $configPath -Encoding UTF8 -Force
    Write-Host "✓ Configuration file created at $configPath" -ForegroundColor Green
}

function Set-WindowsDNS {
    Write-Host "`nConfiguring Windows DNS settings..." -ForegroundColor Cyan
    
    $originalDNS = @{}
    
    Get-NetAdapter | Where-Object {$_.Status -eq "Up"} | ForEach-Object {
        $adapterName = $_.Name
        $currentDNS = (Get-DnsClientServerAddress -InterfaceAlias $adapterName -AddressFamily IPv4).ServerAddresses
        
        $originalDNS[$adapterName] = $currentDNS
        
        if ($DryRun) {
            Write-Host "[DRY RUN] Would set DNS for '$adapterName' to 127.0.0.1" -ForegroundColor Yellow
            Write-Host "  Current DNS: $($currentDNS -join ', ')" -ForegroundColor Gray
        } else {
            Set-DnsClientServerAddress -InterfaceAlias $adapterName -ServerAddresses "127.0.0.1"
            Write-Host "✓ DNS set to 127.0.0.1 for adapter: $adapterName" -ForegroundColor Green
        }
    }
    
    $backupPath = "$env:USERPROFILE\.unbound_dns_backup.json"
    if (-not $DryRun) {
        $originalDNS | ConvertTo-Json | Out-File -FilePath $backupPath -Encoding UTF8
        Write-Host "✓ Original DNS settings backed up to: $backupPath" -ForegroundColor Green
    }
}

function Start-UnboundService {
    Write-Host "`nStarting Unbound service..." -ForegroundColor Cyan
    
    $serviceName = "unbound"
    $unboundExe = "C:\Program Files\Unbound\unbound.exe"
    
    if (-not (Test-Path $unboundExe)) {
        Write-Error "Unbound executable not found at: $unboundExe"
        exit 1
    }
    
    if ($DryRun) {
        Write-Host "[DRY RUN] Would register and start Unbound service" -ForegroundColor Yellow
        return
    }
    
    $service = Get-Service -Name $serviceName -ErrorAction SilentlyContinue
    
    if ($null -eq $service) {
        & $unboundExe install
        Write-Host "✓ Unbound service registered" -ForegroundColor Green
    }
    
    Start-Service -Name $serviceName
    Set-Service -Name $serviceName -StartupType Automatic
    
    Start-Sleep -Seconds 2
    
    $serviceStatus = (Get-Service -Name $serviceName).Status
    if ($serviceStatus -eq "Running") {
        Write-Host "✓ Unbound service is running" -ForegroundColor Green
    } else {
        Write-Error "Unbound service failed to start. Status: $serviceStatus"
        exit 1
    }
}

function Test-Installation {
    Write-Host "`nVerifying installation..." -ForegroundColor Cyan
    
    if ($DryRun) {
        Write-Host "[DRY RUN] Would test DNS resolution" -ForegroundColor Yellow
        return
    }
    
    Start-Sleep -Seconds 2
    
    Clear-DnsClientCache
    
    try {
        $result = Resolve-DnsName -Name "google.com" -Server "127.0.0.1" -Type A -ErrorAction Stop
        Write-Host "✓ DNS resolution test successful" -ForegroundColor Green
        Write-Host "  Resolved google.com to: $($result[0].IPAddress)" -ForegroundColor Gray
    } catch {
        Write-Error "DNS resolution test failed: $_"
        exit 1
    }
    
    Write-Host "`n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Green
    Write-Host "Installation complete!" -ForegroundColor Green
    Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Green
    Write-Host "`nUnbound is now running with the following configuration:"
    Write-Host "  • Multi-provider DNS failover (Cloudflare → Quad9 → Google)"
    Write-Host "  • DNS-over-TLS encryption"
    Write-Host "  • Aggressive caching for performance"
    Write-Host "  • 24-hour survival mode (serves stale cache)"
    Write-Host "`nUseful commands:"
    Write-Host "  • Check service status: Get-Service unbound"
    Write-Host "  • View logs: Get-Content 'C:\Program Files\Unbound\unbound.log' -Tail 50"
    Write-Host "  • Restart service: Restart-Service unbound"
    Write-Host "  • Uninstall: .\install_windows.ps1 -Uninstall"
}

function Uninstall-Unbound {
    Write-Host "`nUninstalling Unbound DNS Resolver..." -ForegroundColor Cyan
    
    $backupPath = "$env:USERPROFILE\.unbound_dns_backup.json"
    
    if (Test-Path $backupPath) {
        Write-Host "Restoring original DNS settings..." -ForegroundColor Yellow
        
        if ($DryRun) {
            Write-Host "[DRY RUN] Would restore DNS settings from backup" -ForegroundColor Yellow
        } else {
            $originalDNS = Get-Content $backupPath | ConvertFrom-Json
            
            $originalDNS.PSObject.Properties | ForEach-Object {
                $adapterName = $_.Name
                $dnsServers = $_.Value
                
                if ($dnsServers -and $dnsServers.Count -gt 0) {
                    Set-DnsClientServerAddress -InterfaceAlias $adapterName -ServerAddresses $dnsServers
                    Write-Host "✓ Restored DNS for adapter: $adapterName" -ForegroundColor Green
                } else {
                    Set-DnsClientServerAddress -InterfaceAlias $adapterName -ResetServerAddresses
                    Write-Host "✓ Reset DNS to automatic for adapter: $adapterName" -ForegroundColor Green
                }
            }
            
            Remove-Item $backupPath -Force
        }
    } else {
        Write-Host "No backup found. Resetting DNS to automatic..." -ForegroundColor Yellow
        
        if (-not $DryRun) {
            Get-NetAdapter | Where-Object {$_.Status -eq "Up"} | ForEach-Object {
                Set-DnsClientServerAddress -InterfaceAlias $_.Name -ResetServerAddresses
                Write-Host "✓ Reset DNS for adapter: $($_.Name)" -ForegroundColor Green
            }
        }
    }
    
    $serviceName = "unbound"
    $service = Get-Service -Name $serviceName -ErrorAction SilentlyContinue
    
    if ($service) {
        if ($DryRun) {
            Write-Host "[DRY RUN] Would stop and remove Unbound service" -ForegroundColor Yellow
        } else {
            Stop-Service -Name $serviceName -Force
            & "C:\Program Files\Unbound\unbound.exe" remove
            Write-Host "✓ Unbound service removed" -ForegroundColor Green
        }
    }
    
    if ($DryRun) {
        Write-Host "[DRY RUN] Would uninstall: choco uninstall unbound -y" -ForegroundColor Yellow
    } else {
        choco uninstall unbound -y
        Write-Host "✓ Unbound uninstalled" -ForegroundColor Green
    }
    
    Write-Host "`n✓ Uninstallation complete!" -ForegroundColor Green
}

if ($Uninstall) {
    Test-AdminPrivileges
    Uninstall-Unbound
} else {
    Test-AdminPrivileges
    Install-Unbound
    Set-WindowsDNS
    Start-UnboundService
    Test-Installation
}
