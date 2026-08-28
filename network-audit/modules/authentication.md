# Authentication Module

## Data Collection (run all in parallel)

```powershell
# Domain membership
(Get-WmiObject Win32_ComputerSystem).PartOfDomain

# NTLM compatibility level (5=NTLMv2 only, 4=NTLMv2, 3=NTLMv2 if negotiated, 1-2=NTLMv1 allowed, 0=LM+NTLM)
Get-ItemProperty HKLM:\SYSTEM\CurrentControlSet\Control\Lsa -Name LmCompatibilityLevel -ErrorAction SilentlyContinue

# WDigest (1=plaintext creds in RAM, 0=disabled)
Get-ItemProperty HKLM:\SYSTEM\CurrentControlSet\Control\SecurityProviders\WDigest -Name UseLogonCredential -ErrorAction SilentlyContinue

# Guest account
Get-LocalUser -Name Guest | Select-Object Name, Enabled, LastLogon

# All local administrator accounts
Get-LocalGroupMember -Group "Administrators" | Select-Object Name, ObjectClass, PrincipalSource

# Password policy
net accounts

# Cached logon count (number of domain credentials cached offline)
Get-ItemProperty 'HKLM:\SOFTWARE\Microsoft\Windows\NT\CurrentVersion\Winlogon' -Name CachedLogonsCount -ErrorAction SilentlyContinue

# Credential Guard
(Get-ComputerInfo).DeviceGuardSecurityServicesRunning

# Kerberos encryption types
Get-ItemProperty 'HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Policies\System\Kerberos\Parameters' -ErrorAction SilentlyContinue

# Protected Users group (domain only — check PartOfDomain first)
if ((Get-WmiObject Win32_ComputerSystem).PartOfDomain) {
    Get-ADGroupMember "Protected Users" -ErrorAction SilentlyContinue | Select-Object Name, SamAccountName
}
```

## Risk Indicators

| Finding | Condition | CVSS Vector | Score |
|---|---|---|---|
| NTLMv1 allowed | `LmCompatibilityLevel` ≤ 3 or key absent | AV:A/AC:H/PR:N/UI:N/C:H/I:H/A:N | **7.5 High** |
| WDigest enabled | `UseLogonCredential = 1` | AV:L/AC:L/PR:L/UI:N/C:H/I:N/A:N | **5.5 Medium** |
| Guest account enabled | `Enabled = True` | AV:N/AC:L/PR:N/UI:N/C:L/I:N/A:N | **5.3 Medium** |
| Excessive local admins | More than 2 accounts in Administrators group | AV:L/AC:L/PR:L/UI:N/C:H/I:H/A:N | **6.1 Medium** |
| Weak password min length | `Minimum password length` < 14 | AV:N/AC:H/PR:N/UI:N/C:H/I:N/A:N | **5.9 Medium** |
| No account lockout | `Lockout threshold = 0` | AV:N/AC:L/PR:N/UI:N/C:H/I:N/A:N | **7.5 High** |
| High cached logon count | `CachedLogonsCount` > 2 | AV:L/AC:L/PR:L/UI:N/C:H/I:N/A:N | **4.7 Medium** |

## Analysis Notes

**NTLM level:** Level 5 is the recommended setting (send NTLMv2 only, refuse LM and NTLMv1). Levels 0–3 allow NTLMv1 which is crackable via pass-the-hash and relay attacks.

**WDigest:** When enabled, Windows stores a plaintext copy of the user's password in LSASS memory. Mimikatz and similar tools can extract it. Should always be disabled (0) on modern Windows.

**Local admins:** Every extra admin account is a lateral movement path. Acceptable accounts are the built-in Administrator (should be disabled or renamed) and the primary user account. Service accounts should never be in Administrators.

**Password policy:** CIS Benchmark recommends: min length 14, complexity enabled, lockout after 5 attempts, lockout duration 15+ minutes.

**Cached logons:** Domain credentials cached locally allow offline brute-force. Setting to 1–2 is a reasonable balance for laptops; servers should be 0.
