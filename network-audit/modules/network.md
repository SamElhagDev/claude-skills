# Network Module

## Data Collection (run all in parallel)

```powershell
# Adapters
Get-NetAdapter | Select-Object Name, Status, MacAddress, LinkSpeed

# Full IP config
ipconfig /all

# TCP listeners
Get-NetTCPConnection | Where-Object State -eq 'Listen' |
  Select-Object LocalAddress, LocalPort | Sort-Object LocalPort

# UDP endpoints
Get-NetUDPEndpoint | Select-Object LocalAddress, LocalPort | Sort-Object LocalPort

# Established connections
Get-NetTCPConnection | Where-Object State -eq 'Established' |
  Select-Object LocalAddress, LocalPort, RemoteAddress, RemotePort |
  Sort-Object RemoteAddress

# Routing table
Get-NetRoute | Where-Object AddressFamily -eq 'IPv4' |
  Select-Object DestinationPrefix, NextHop, RouteMetric, InterfaceAlias |
  Sort-Object RouteMetric

# ARP neighbours
Get-NetNeighbor | Where-Object State -eq 'Reachable' |
  Select-Object IPAddress, LinkLayerAddress, State

# SMB shares
Get-SmbShare | Select-Object Name, Path, ScopeName, Description

# Hosts file (non-comment, non-blank)
Get-Content C:\Windows\System32\drivers\etc\hosts |
  Where-Object { $_ -notmatch '^\s*#' -and $_.Trim() -ne '' }

# DNS cache (sample)
Get-DnsClientCache | Select-Object -First 20

# IPv6 addresses
Get-NetIPAddress | Where-Object AddressFamily -eq 'IPv6' |
  Select-Object InterfaceAlias, IPAddress, PrefixLength

# SMBv1 status
Get-SmbServerConfiguration | Select-Object EnableSMB1Protocol

# TLS 1.0 server registry
Get-ItemProperty 'HKLM:\SYSTEM\CurrentControlSet\Control\SecurityProviders\SCHANNEL\Protocols\TLS 1.0\Server' `
  -ErrorAction SilentlyContinue | Select-Object Enabled, DisabledByDefault

# TLS 1.1 server registry
Get-ItemProperty 'HKLM:\SYSTEM\CurrentControlSet\Control\SecurityProviders\SCHANNEL\Protocols\TLS 1.1\Server' `
  -ErrorAction SilentlyContinue | Select-Object Enabled, DisabledByDefault

# Wi-Fi profiles
netsh wlan show profiles
```

## Risk Indicators

| Finding | Condition | CVSS Vector | Score |
|---|---|---|---|
| SMBv1 enabled | `EnableSMB1Protocol = True` | AV:N/AC:L/PR:N/UI:N/C:H/I:H/A:H | **9.8 Critical** |
| Non-standard SMB share | Share name not in {C$, ADMIN$, IPC$, print$} | AV:N/AC:L/PR:L/UI:N/C:H/I:H/A:N | **7.6 High** |
| TLS 1.0 server enabled | Registry `Enabled = 1` or key absent (default-on) | AV:N/AC:H/PR:N/UI:R/C:L/I:L/A:N | **5.4 Medium** |
| TLS 1.1 server enabled | Registry `Enabled = 1` or key absent (default-on) | AV:N/AC:H/PR:N/UI:R/C:L/I:L/A:N | **4.8 Medium** |
| Service on 0.0.0.0 (non-standard port) | Non-system port listening on all interfaces | AV:N/AC:L/PR:N/UI:N/C:L/I:N/A:N | **5.3 Medium** |
| Suspicious hosts file entry | Entry not matching Docker/Tailscale patterns | AV:L/AC:L/PR:H/UI:N/C:H/I:H/A:N | **6.3 Medium** |
| Unknown external connection | Established TCP to unrecognised IP | AV:N/AC:H/PR:N/UI:R/C:L/I:N/A:N | **3.7 Low** |

## Analysis Notes

**Port classification:** Known system ports: RPC/135, SMB/445, Hyper-V/2179, WSD/5357, Windows Update Delivery/7680, NFS/2049+111, RDP/3389. Any unlisted port on `0.0.0.0` is a finding. Identify owner with:
`Get-Process -Id (Get-NetTCPConnection -LocalPort <port>).OwningProcess | Select-Object Name, Id`

**SMB shares:** Acceptable defaults are `C$`, `ADMIN$`, `IPC$`, `print$`. Any additional share is a finding. Note path and who has access: `Get-SmbShareAccess -Name <share>`.

**Hosts file:** Acceptable entries: Docker (`host.docker.internal`, `gateway.docker.internal`, `kubernetes.docker.internal`), Tailscale device names. Anything else is a finding.

**TLS:** If the registry key is absent, Windows may still negotiate TLS 1.0/1.1. Absence is treated as enabled unless `DisabledByDefault = 1` is set.

**Wi-Fi:** For each profile, run `netsh wlan show profile name="<profile>" key=clear`. Flag: open security type, WEP, or TKIP encryption.
