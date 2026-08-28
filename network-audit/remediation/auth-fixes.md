# Authentication Remediation Commands

---

### NTLMv1 Allowed

**⚠ DESTRUCTIVE** — sets NTLM level to 5 (NTLMv2 only). Legacy clients that only support NTLMv1 will fail to authenticate.

```powershell
Set-ItemProperty HKLM:\SYSTEM\CurrentControlSet\Control\Lsa -Name LmCompatibilityLevel -Value 5 -Type DWord
```

Verify: `Get-ItemProperty HKLM:\SYSTEM\CurrentControlSet\Control\Lsa -Name LmCompatibilityLevel` → `5`

---

### WDigest Enabled

```powershell
Set-ItemProperty HKLM:\SYSTEM\CurrentControlSet\Control\SecurityProviders\WDigest -Name UseLogonCredential -Value 0 -Type DWord
```

Verify: `Get-ItemProperty HKLM:\SYSTEM\CurrentControlSet\Control\SecurityProviders\WDigest -Name UseLogonCredential` → `0`
Note: Takes effect on next logon — current session is not affected.

---

### Guest Account Enabled

```powershell
Disable-LocalUser -Name Guest
```

Verify: `Get-LocalUser -Name Guest | Select-Object Enabled` → `False`

---

### Weak Password Minimum Length

Sets minimum to 14 characters (CIS Benchmark recommendation).

```powershell
net accounts /minpwlen:14
```

Verify: `net accounts` → `Minimum password length: 14`

---

### No Account Lockout

Sets lockout after 5 failed attempts, 15-minute lockout duration.

```powershell
net accounts /lockoutthreshold:5
net accounts /lockoutduration:15
net accounts /lockoutwindow:15
```

Verify: `net accounts` → `Lockout threshold: 5`

---

### High Cached Logon Count

Sets to 1 cached credential (minimum for laptop usability). Use 0 for servers.

**⚠ DESTRUCTIVE** — if the machine is offline and count reaches 0, users cannot log in.

```powershell
Set-ItemProperty 'HKLM:\SOFTWARE\Microsoft\Windows\NT\CurrentVersion\Winlogon' -Name CachedLogonsCount -Value 1
```

Verify: `Get-ItemProperty 'HKLM:\SOFTWARE\Microsoft\Windows\NT\CurrentVersion\Winlogon' -Name CachedLogonsCount` → `1`
