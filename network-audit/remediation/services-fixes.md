# Services Remediation Commands

---

### Unquoted Service Path

Replace `<ServiceName>` and `<FullPathWithSpaces>` with the flagged values.

**⚠ DESTRUCTIVE** — reconfigures the service binary path. Test in a maintenance window.

```powershell
sc.exe config "<ServiceName>" binPath= "\"<FullPathWithSpaces>\""
```

Verify: `Get-WmiObject Win32_Service -Filter "Name='<ServiceName>'" | Select-Object PathName` → path is now quoted

---

### Auto-Start Service with Unsigned Binary

Replace `<ServiceName>` with the flagged service. This disables the service.

**⚠ DESTRUCTIVE** — stopping and disabling may break dependent functionality. Investigate the binary first.

```powershell
Stop-Service -Name "<ServiceName>" -Force
Set-Service -Name "<ServiceName>" -StartupType Disabled
```

Verify: `Get-Service "<ServiceName>" | Select-Object Status, StartType` → `Stopped, Disabled`
