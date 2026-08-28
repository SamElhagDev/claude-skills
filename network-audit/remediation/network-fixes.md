# Network Remediation Commands

For each fix below: show the command to the user, get confirmation, then run it.
Entries marked **⚠ DESTRUCTIVE** require the extra confirmation prompt.

---

### SMBv1 Enabled

**⚠ DESTRUCTIVE** — disables SMBv1 server and client. Existing SMBv1 sessions will be terminated.

```powershell
Set-SmbServerConfiguration -EnableSMB1Protocol $false -Force
Set-SmbClientConfiguration -EnableSMB1Protocol $false -Force
```

Verify: `Get-SmbServerConfiguration | Select-Object EnableSMB1Protocol` → should return `False`

---

### Non-Standard SMB Share

Replace `<ShareName>` with the flagged share name.

**⚠ DESTRUCTIVE** — removes the share. The underlying folder is not deleted.

```powershell
Remove-SmbShare -Name "<ShareName>" -Force
```

Verify: `Get-SmbShare | Where-Object Name -eq "<ShareName>"` → should return nothing

---

### TLS 1.0 Server Enabled

```powershell
$path = 'HKLM:\SYSTEM\CurrentControlSet\Control\SecurityProviders\SCHANNEL\Protocols\TLS 1.0\Server'
If (-not (Test-Path $path)) { New-Item -Path $path -Force | Out-Null }
Set-ItemProperty -Path $path -Name 'Enabled' -Value 0 -Type DWord
Set-ItemProperty -Path $path -Name 'DisabledByDefault' -Value 1 -Type DWord
```

Verify: `Get-ItemProperty $path | Select-Object Enabled, DisabledByDefault` → `Enabled=0, DisabledByDefault=1`
Note: Requires reboot to take effect.

---

### TLS 1.1 Server Enabled

```powershell
$path = 'HKLM:\SYSTEM\CurrentControlSet\Control\SecurityProviders\SCHANNEL\Protocols\TLS 1.1\Server'
If (-not (Test-Path $path)) { New-Item -Path $path -Force | Out-Null }
Set-ItemProperty -Path $path -Name 'Enabled' -Value 0 -Type DWord
Set-ItemProperty -Path $path -Name 'DisabledByDefault' -Value 1 -Type DWord
```

Verify: `Get-ItemProperty $path | Select-Object Enabled, DisabledByDefault` → `Enabled=0, DisabledByDefault=1`
Note: Requires reboot to take effect.

---

### Suspicious Hosts File Entry

Replace `<entry>` with the flagged line.

```powershell
$hostsPath = 'C:\Windows\System32\drivers\etc\hosts'
(Get-Content $hostsPath) | Where-Object { $_ -notmatch [regex]::Escape('<entry>') } | Set-Content $hostsPath
```

Verify: `Get-Content $hostsPath | Select-String '<entry>'` → should return nothing

---

### Identify Unknown Port on 0.0.0.0

Replace `<port>` with the flagged port number.

```powershell
$pid = (Get-NetTCPConnection -LocalPort <port> -ErrorAction SilentlyContinue).OwningProcess | Select-Object -First 1
Get-Process -Id $pid | Select-Object Name, Id, Path
Get-WmiObject Win32_Service | Where-Object { $_.ProcessId -eq $pid } | Select-Object Name, DisplayName, StartName
```
