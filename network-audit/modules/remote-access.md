# Remote Access Module

## Data Collection (run all in parallel)

```powershell
# RDP enabled/disabled (0=enabled, 1=disabled)
Get-ItemProperty 'HKLM:\System\CurrentControlSet\Control\Terminal Server' -Name fDenyTSConnections

# RDP Network Level Authentication (1=NLA required, 0=NLA not required)
Get-ItemProperty 'HKLM:\System\CurrentControlSet\Control\Terminal Server\WinStations\RDP-Tcp' -Name UserAuthentication

# RDP encryption level (1=Low, 2=Client-compat, 3=High, 4=FIPS)
Get-ItemProperty 'HKLM:\System\CurrentControlSet\Control\Terminal Server\WinStations\RDP-Tcp' -Name MinEncryptionLevel

# WinRM service status
Get-Service WinRM | Select-Object Name, Status, StartType

# WinRM configuration
winrm get winrm/config/client 2>$null
winrm get winrm/config/service 2>$null

# WinRM trusted hosts
Get-Item WSMan:\localhost\Client\TrustedHosts -ErrorAction SilentlyContinue

# OpenSSH server
Get-Service sshd -ErrorAction SilentlyContinue | Select-Object Name, Status, StartType

# SSH admin authorized keys
Get-Content "$env:ProgramData\ssh\administrators_authorized_keys" -ErrorAction SilentlyContinue

# WMI firewall rules
Get-NetFirewallRule | Where-Object { $_.DisplayName -like '*WMI*' } |
  Select-Object DisplayName, Enabled, Action, Direction

# Inbound firewall rules for sensitive ports
Get-NetFirewallRule | Where-Object {
    $_.Direction -eq 'Inbound' -and $_.Action -eq 'Allow' -and $_.Enabled -eq 'True'
} | Get-NetFirewallPortFilter | Where-Object {
    $_.LocalPort -in @('3389','5985','5986','22','135','445','23','21')
} | Select-Object LocalPort, Protocol
```

## Risk Indicators

| Finding | Condition | CVSS Vector | Score |
|---|---|---|---|
| RDP without NLA | `UserAuthentication = 0` while RDP is enabled | AV:N/AC:L/PR:N/UI:R/C:H/I:H/A:H | **8.8 High** |
| RDP encryption below High | `MinEncryptionLevel` < 3 | AV:N/AC:H/PR:L/UI:N/C:H/I:N/A:N | **5.9 Medium** |
| WinRM enabled with open trusted hosts | Service running + `TrustedHosts = *` | AV:N/AC:L/PR:L/UI:N/C:H/I:H/A:N | **7.1 High** |
| WinRM enabled (any config) | Service `Status = Running` | AV:N/AC:H/PR:L/UI:N/C:L/I:L/A:N | **4.2 Medium** |
| SSH server running | `sshd Status = Running` | AV:N/AC:L/PR:N/UI:N/C:L/I:L/A:N | **6.5 Medium** |
| SSH admin authorized keys present | File non-empty | AV:N/AC:L/PR:N/UI:N/C:H/I:H/A:N | **7.5 High** |
| WMI remote access enabled | WMI firewall rule `Enabled = True, Action = Allow` | AV:N/AC:L/PR:H/UI:N/C:H/I:H/A:H | **7.2 High** |
| Telnet port open in firewall | Port 23 allowed inbound | AV:N/AC:L/PR:N/UI:N/C:H/I:H/A:H | **9.8 Critical** |
| FTP port open in firewall | Port 21 allowed inbound | AV:N/AC:L/PR:N/UI:N/C:H/I:N/A:N | **7.5 High** |

## Analysis Notes

**RDP + NLA:** Without NLA, any unauthenticated user reaches the Windows login screen — a large attack surface for brute-force and BlueKeep-class vulnerabilities. With NLA, authentication happens before the RDP session is established.

**WinRM trusted hosts `*`:** Means this machine will send credentials to ANY machine claiming to be a WinRM server — trivially exploitable in a man-in-the-middle position.

**SSH authorized keys:** Keys in `administrators_authorized_keys` grant admin shell access. Each key should be audited and attributed to a known user.
