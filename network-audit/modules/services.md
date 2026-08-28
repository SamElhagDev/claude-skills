# Services Module

## Data Collection (run all in parallel)

```powershell
# Running services with their listening TCP ports
$listeners = Get-NetTCPConnection | Where-Object State -eq 'Listen' |
  Select-Object LocalPort, OwningProcess
Get-Service | Where-Object Status -eq 'Running' | ForEach-Object {
    $svc = Get-WmiObject Win32_Service -Filter "Name='$($_.Name)'"
    $pids = (Get-WmiObject Win32_ServiceProcess | Where-Object ServiceName -eq $_.Name).ProcessId
    $ports = $listeners | Where-Object OwningProcess -in $pids | Select-Object -ExpandProperty LocalPort
    [PSCustomObject]@{
        Name = $_.Name
        DisplayName = $_.DisplayName
        StartName = $svc.StartName
        Ports = ($ports -join ', ')
        PathName = $svc.PathName
    }
} | Where-Object { $_.Ports -ne '' } | Sort-Object Name

# Services running as LocalSystem
Get-WmiObject Win32_Service |
  Where-Object { $_.StartName -eq 'LocalSystem' -and $_.State -eq 'Running' } |
  Select-Object Name, DisplayName, PathName

# Unquoted service paths (path contains space and is not quoted)
Get-WmiObject Win32_Service |
  Where-Object { $_.PathName -notmatch '^"' -and $_.PathName -match ' ' -and $_.PathName -notmatch '^[A-Z]:\\Windows\\' } |
  Select-Object Name, DisplayName, PathName, StartName

# Services with auto-start and unsigned binary
Get-WmiObject Win32_Service | Where-Object { $_.StartMode -eq 'Auto' -and $_.PathName } | ForEach-Object {
    $path = $_.PathName -replace '^"([^"]+)".*', '$1' -replace '^(\S+).*', '$1'
    if (Test-Path $path) {
        $sig = Get-AuthenticodeSignature $path
        if ($sig.Status -ne 'Valid') {
            [PSCustomObject]@{ Name = $_.Name; Path = $path; SignatureStatus = $sig.Status }
        }
    }
}
```

## Risk Indicators

| Finding | Condition | CVSS Vector | Score |
|---|---|---|---|
| Unquoted service path | Path has space, not quoted, not in System32 | AV:L/AC:L/PR:L/UI:N/C:H/I:H/A:H | **7.8 High** |
| Auto-start service with unsigned binary | `SignatureStatus` ≠ Valid | AV:L/AC:L/PR:L/UI:N/C:H/I:H/A:H | **7.3 High** |
| Unnecessary service running as SYSTEM | SYSTEM-owned service with network port, not required by OS | AV:N/AC:L/PR:L/UI:N/C:H/I:H/A:H | **8.8 High** |

## Analysis Notes

**Unquoted paths:** If a service binary path like `C:\Program Files\My App\service.exe` is unquoted, Windows tries `C:\Program.exe`, then `C:\Program Files\My.exe` before finding the real binary. An attacker with write access to `C:\` can plant `Program.exe` to hijack execution.

**SYSTEM services:** Not all SYSTEM services are problematic — SCM, Winlogon, etc. are expected. Flag services running as SYSTEM that have external network ports and are not part of Windows core (`PathName` outside `System32`/`SysWOW64`).

**Unsigned binaries:** All legitimate Windows services are signed by Microsoft. Third-party services should be signed by their vendor. Unsigned auto-start service binaries are either malware or misconfigured software.
