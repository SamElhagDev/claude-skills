# Patching Remediation Commands

---

### Pending Critical / Important Updates

Installs all pending updates. Does not auto-reboot — a manual reboot is required after.

**⚠ DESTRUCTIVE** — applies system patches. Schedule during a maintenance window if this is a production server.

```powershell
if (-not (Get-Module -ListAvailable PSWindowsUpdate)) {
    Install-Module PSWindowsUpdate -Force -Scope CurrentUser
}
Import-Module PSWindowsUpdate
Get-WindowsUpdate -Install -AcceptAll -AutoReboot:$false -Verbose
```

Verify: `Get-HotFix | Sort-Object InstalledOn -Descending | Select-Object -First 3` → new KBs appear after reboot.

---

### Defender Definitions Outdated

```powershell
Update-MpSignature
```

Verify: `Get-MpComputerStatus | Select-Object AntivirusSignatureLastUpdated` → timestamp is within last hour.

---

### Defender Real-Time Protection Disabled

**⚠ DESTRUCTIVE** — re-enables real-time protection. If disabled by a policy or another AV product, this may fail.

```powershell
Set-MpPreference -DisableRealtimeMonitoring $false
```

Verify: `Get-MpComputerStatus | Select-Object RealTimeProtectionEnabled` → `True`

---

### Windows Update Service Disabled

**⚠ DESTRUCTIVE** — re-enables and starts the Windows Update service.

```powershell
Set-Service wuauserv -StartupType Automatic
Start-Service wuauserv
```

Verify: `Get-Service wuauserv | Select-Object Status, StartType` → `Running, Automatic`

---

### Auto-Updates Disabled by Policy

This removes the policy key, restoring default Windows Update behavior.

**⚠ DESTRUCTIVE** — if the policy was set intentionally (e.g. WSUS-managed environment), removing it changes patching behavior.

```powershell
Remove-ItemProperty 'HKLM:\SOFTWARE\Policies\Microsoft\Windows\WindowsUpdate\AU' -Name 'NoAutoUpdate' -ErrorAction SilentlyContinue
Remove-ItemProperty 'HKLM:\SOFTWARE\Policies\Microsoft\Windows\WindowsUpdate\AU' -Name 'AUOptions' -ErrorAction SilentlyContinue
```

Verify: `Get-ItemProperty 'HKLM:\SOFTWARE\Policies\Microsoft\Windows\WindowsUpdate\AU' -ErrorAction SilentlyContinue` → keys are absent or empty.
