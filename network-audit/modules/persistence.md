# Persistence Module

## Data Collection (run all in parallel)

```powershell
# Non-Microsoft scheduled tasks
Get-ScheduledTask | Where-Object { $_.TaskPath -notlike '\Microsoft\*' } |
  Select-Object TaskName, TaskPath, State,
    @{N='Action';E={($_.Actions | ForEach-Object { $_.Execute + ' ' + $_.Arguments }) -join '; '}} |
  Sort-Object TaskPath, TaskName

# HKLM Run keys
Get-ItemProperty 'HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Run' -ErrorAction SilentlyContinue
Get-ItemProperty 'HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\RunOnce' -ErrorAction SilentlyContinue

# HKCU Run keys (current user)
Get-ItemProperty 'HKCU:\SOFTWARE\Microsoft\Windows\CurrentVersion\Run' -ErrorAction SilentlyContinue
Get-ItemProperty 'HKCU:\SOFTWARE\Microsoft\Windows\CurrentVersion\RunOnce' -ErrorAction SilentlyContinue

# Startup folder (all users)
Get-ChildItem "$env:ProgramData\Microsoft\Windows\Start Menu\Programs\Startup" -ErrorAction SilentlyContinue |
  Select-Object Name, FullName, LastWriteTime

# Startup folder (current user)
Get-ChildItem "$env:APPDATA\Microsoft\Windows\Start Menu\Programs\Startup" -ErrorAction SilentlyContinue |
  Select-Object Name, FullName, LastWriteTime

# WMI event filters (persistence trigger)
Get-WMIObject -Namespace root\subscription -Class __EventFilter -ErrorAction SilentlyContinue |
  Select-Object Name, Query, QueryLanguage

# WMI event consumers (persistence payload)
Get-WMIObject -Namespace root\subscription -Class __EventConsumer -ErrorAction SilentlyContinue |
  Select-Object Name, ScriptText, CommandLineTemplate

# WMI filter-to-consumer bindings (links trigger to payload)
Get-WMIObject -Namespace root\subscription -Class __FilterToConsumerBinding -ErrorAction SilentlyContinue |
  Select-Object Filter, Consumer

# LSA authentication packages (extra packages = suspicious)
Get-ItemProperty HKLM:\SYSTEM\CurrentControlSet\Control\Lsa -Name 'Authentication Packages' -ErrorAction SilentlyContinue

# LSA notification packages
Get-ItemProperty HKLM:\SYSTEM\CurrentControlSet\Control\Lsa -Name 'Notification Packages' -ErrorAction SilentlyContinue

# Edge extensions (current user profile)
Get-ChildItem "$env:LOCALAPPDATA\Microsoft\Edge\User Data\Default\Extensions" -ErrorAction SilentlyContinue |
  Select-Object Name, LastWriteTime
```

## Risk Indicators

| Finding | Condition | CVSS Vector | Score |
|---|---|---|---|
| WMI event subscription present | Any `__FilterToConsumerBinding` exists | AV:L/AC:L/PR:H/UI:N/C:H/I:H/A:H | **8.2 High** |
| Non-Microsoft scheduled task with suspicious path | Task action runs from `%TEMP%`, `%APPDATA%`, or `C:\Users\` | AV:L/AC:L/PR:L/UI:N/C:H/I:H/A:N | **7.8 High** |
| Unknown HKLM autorun entry | Entry not attributable to installed software | AV:L/AC:L/PR:H/UI:N/C:H/I:H/A:N | **6.7 Medium** |
| Unknown HKCU autorun entry | Entry not attributable to installed software | AV:L/AC:L/PR:L/UI:N/C:H/I:H/A:N | **7.3 High** |
| Non-standard LSA package | Extra package beyond {msv1_0, kerberos, wdigest, tspkg, pku2u} | AV:L/AC:L/PR:H/UI:N/C:H/I:H/A:H | **8.2 High** |
| Unknown startup folder item | File not attributable to installed software | AV:L/AC:L/PR:L/UI:R/C:H/I:H/A:N | **6.5 Medium** |

## Analysis Notes

**WMI subscriptions:** All three objects (`__EventFilter`, `__EventConsumer`, `__FilterToConsumerBinding`) must exist for a working subscription. Finding any of the three is suspicious. Finding all three linked is a confirmed persistence mechanism. Legitimate tools that use WMI subscriptions include some AV/EDR products — verify attribution before removing.

**LSA packages:** The standard set is `msv1_0 kerberos wdigest tspkg pku2u`. Any additional DLL in this list is loaded into LSASS at boot and has access to all credentials — a known malware technique.

**Scheduled tasks:** Focus on tasks with actions pointing to `%TEMP%`, `%APPDATA%`, `C:\Users\`, or with Base64-encoded PowerShell arguments (`-EncodedCommand`).
