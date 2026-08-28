# Patching Module

## Data Collection (run all in parallel)

```powershell
# Windows version and build
Get-ComputerInfo | Select-Object WindowsProductName, WindowsVersion, OsBuildNumber, OsLastBootUpTime

# Most recent hotfix
Get-HotFix | Sort-Object InstalledOn -Descending | Select-Object -First 5 |
  Select-Object HotFixID, InstalledOn, Description

# Pending update count
try {
    $session = New-Object -ComObject Microsoft.Update.Session
    $searcher = $session.CreateUpdateSearcher()
    $result = $searcher.Search("IsInstalled=0 and IsHidden=0")
    [PSCustomObject]@{
        PendingCount = $result.Updates.Count
        CriticalCount = ($result.Updates | Where-Object { $_.MsrcSeverity -eq 'Critical' }).Count
        ImportantCount = ($result.Updates | Where-Object { $_.MsrcSeverity -eq 'Important' }).Count
    }
} catch {
    "Windows Update COM object unavailable: $_"
}

# Windows Defender status
Get-MpComputerStatus | Select-Object `
    AMRunningMode, RealTimeProtectionEnabled, `
    AntivirusSignatureLastUpdated, AntivirusSignatureVersion, `
    NISSignatureLastUpdated, BehaviorMonitorEnabled, `
    IoavProtectionEnabled, AntispywareEnabled

# .NET runtime versions
Get-ChildItem 'HKLM:\SOFTWARE\Microsoft\NET Framework Setup\NDP' -Recurse |
  Get-ItemProperty -Name Version, Release -ErrorAction SilentlyContinue |
  Where-Object { $_.PSChildName -eq 'Full' -or $_.PSChildName -match '^v\d' } |
  Select-Object PSPath, Version, Release | Sort-Object Version -Descending

# Windows Update service status
Get-Service wuauserv | Select-Object Name, Status, StartType

# Automatic update policy
Get-ItemProperty 'HKLM:\SOFTWARE\Policies\Microsoft\Windows\WindowsUpdate\AU' -ErrorAction SilentlyContinue |
  Select-Object AUOptions, NoAutoUpdate, ScheduledInstallDay, ScheduledInstallTime
```

## Risk Indicators

| Finding | Condition | CVSS Vector | Score |
|---|---|---|---|
| Pending critical updates | `CriticalCount` > 0 | AV:N/AC:L/PR:N/UI:N/C:H/I:H/A:H | **9.0 Critical** |
| Pending important updates | `ImportantCount` > 0 | AV:N/AC:L/PR:L/UI:N/C:H/I:H/A:N | **7.6 High** |
| Defender definitions > 7 days old | `AntivirusSignatureLastUpdated` > 7 days ago | AV:N/AC:H/PR:N/UI:R/C:L/I:L/A:N | **4.2 Medium** |
| Defender real-time protection off | `RealTimeProtectionEnabled = False` | AV:N/AC:L/PR:N/UI:N/C:H/I:H/A:H | **9.3 Critical** |
| Windows Update service disabled | `wuauserv StartType = Disabled` | AV:N/AC:L/PR:N/UI:N/C:H/I:H/A:H | **7.5 High** |
| Auto-updates disabled by policy | `NoAutoUpdate = 1` | AV:N/AC:L/PR:N/UI:N/C:H/I:H/A:N | **5.8 Medium** |
| Last hotfix > 60 days ago | `InstalledOn` > 60 days ago | AV:N/AC:L/PR:N/UI:N/C:H/I:H/A:H | **7.5 High** |

## Analysis Notes

**Defender definitions:** Microsoft releases definition updates multiple times per day. Definitions older than 7 days indicate the machine is not receiving updates and is blind to recent malware.

**Windows Update service:** If disabled, the machine cannot receive any patches. This is sometimes done in enterprise environments where WSUS/SCCM manages patching — check for WSUS policy (`HKLM:\SOFTWARE\Policies\Microsoft\Windows\WindowsUpdate`) before flagging.

**Pending critical updates:** Any pending critical security update is a Critical finding regardless of age — patch it this session.
