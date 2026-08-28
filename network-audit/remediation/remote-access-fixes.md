# Remote Access Remediation Commands

---

### RDP Without NLA

Enables Network Level Authentication for RDP.

```powershell
Set-ItemProperty 'HKLM:\System\CurrentControlSet\Control\Terminal Server\WinStations\RDP-Tcp' -Name UserAuthentication -Value 1
```

Verify: `Get-ItemProperty 'HKLM:\System\CurrentControlSet\Control\Terminal Server\WinStations\RDP-Tcp' -Name UserAuthentication` → `1`

---

### RDP Encryption Below High

Sets encryption level to High (3).

```powershell
Set-ItemProperty 'HKLM:\System\CurrentControlSet\Control\Terminal Server\WinStations\RDP-Tcp' -Name MinEncryptionLevel -Value 3
```

Verify: `Get-ItemProperty 'HKLM:\System\CurrentControlSet\Control\Terminal Server\WinStations\RDP-Tcp' -Name MinEncryptionLevel` → `3`

---

### WinRM With Open Trusted Hosts

Clears the trusted hosts list to empty.

**⚠ DESTRUCTIVE** — existing WinRM connections to machines matched by `*` will stop working.

```powershell
Set-Item WSMan:\localhost\Client\TrustedHosts -Value "" -Force
```

Verify: `Get-Item WSMan:\localhost\Client\TrustedHosts` → value is empty

---

### WinRM Enabled (Disable Entirely)

**⚠ DESTRUCTIVE** — disables all remote PowerShell management of this machine.

```powershell
Stop-Service WinRM -Force
Set-Service WinRM -StartupType Disabled
Disable-PSRemoting -Force
```

Verify: `Get-Service WinRM | Select-Object Status, StartType` → `Stopped, Disabled`

---

### SSH Server Running (Disable)

**⚠ DESTRUCTIVE** — disables all SSH access to this machine.

```powershell
Stop-Service sshd -Force
Set-Service sshd -StartupType Disabled
```

Verify: `Get-Service sshd | Select-Object Status, StartType` → `Stopped, Disabled`

---

### WMI Remote Access (Disable Firewall Rule)

**⚠ DESTRUCTIVE** — blocks remote WMI queries from all hosts.

```powershell
Get-NetFirewallRule | Where-Object { $_.DisplayName -like '*WMI*' } | Set-NetFirewallRule -Enabled False
```

Verify: `Get-NetFirewallRule | Where-Object { $_.DisplayName -like '*WMI*' } | Select-Object DisplayName, Enabled` → all `False`
