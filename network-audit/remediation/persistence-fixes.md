# Persistence Remediation Commands

---

### WMI Event Subscription (Remove All Three Objects)

Replace `<FilterName>`, `<ConsumerName>` with the names found during the audit.

**⚠ DESTRUCTIVE** — removes the WMI persistence mechanism entirely. Confirm attribution before removing.

```powershell
# Remove binding first (order matters)
Get-WMIObject -Namespace root\subscription -Class __FilterToConsumerBinding |
  Where-Object { $_.Filter -like "*<FilterName>*" } | Remove-WmiObject

# Remove consumer
Get-WMIObject -Namespace root\subscription -Class __EventConsumer |
  Where-Object { $_.Name -eq "<ConsumerName>" } | Remove-WmiObject

# Remove filter
Get-WMIObject -Namespace root\subscription -Class __EventFilter |
  Where-Object { $_.Name -eq "<FilterName>" } | Remove-WmiObject
```

Verify: All three queries return empty results.

---

### Remove Non-Microsoft Scheduled Task

Replace `<TaskName>` and `<TaskPath>` with the flagged values.

**⚠ DESTRUCTIVE** — permanently removes the task.

```powershell
Unregister-ScheduledTask -TaskName "<TaskName>" -TaskPath "<TaskPath>" -Confirm:$false
```

Verify: `Get-ScheduledTask -TaskName "<TaskName>" -ErrorAction SilentlyContinue` → returns nothing

---

### Remove Autorun Registry Entry

Replace `<EntryName>` with the registry value name.

For HKLM (requires admin):
```powershell
Remove-ItemProperty -Path 'HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Run' -Name '<EntryName>'
```

For HKCU (current user):
```powershell
Remove-ItemProperty -Path 'HKCU:\SOFTWARE\Microsoft\Windows\CurrentVersion\Run' -Name '<EntryName>'
```

Verify: `Get-ItemProperty 'HKLM:\...\Run'` → `<EntryName>` no longer appears

---

### Remove Non-Standard LSA Package

**⚠ DESTRUCTIVE** — removing a legitimate LSA package will break authentication. Only remove confirmed malicious entries. Requires reboot.

```powershell
$current = (Get-ItemProperty HKLM:\SYSTEM\CurrentControlSet\Control\Lsa -Name 'Authentication Packages').'Authentication Packages'
$updated = $current | Where-Object { $_ -ne '<PackageName>' }
Set-ItemProperty HKLM:\SYSTEM\CurrentControlSet\Control\Lsa -Name 'Authentication Packages' -Value $updated
```

Note: Changes take effect on next reboot.
