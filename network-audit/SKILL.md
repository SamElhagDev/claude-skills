---
name: network-audit
description: Use when asked to run, perform, or conduct a network audit, network assessment, network scan, network security review, or security posture check on the current machine
---

# Network Audit

## Overview
Full-spectrum Windows security audit. Runs 6 domain modules, scores every finding with CVSS v3.1, presents a report sorted by severity, then offers interactive remediation with per-command confirmation. Local machine only — for remote machines, run Claude Code directly on that machine.

## Audit Sequence

For each module below, in order:
1. Read the module file listed
2. Run ALL its data collection commands **in parallel**
3. Analyze output against the risk indicators defined in that module
4. Assign a CVSS score to each finding using the rubric below
5. Add findings to a running list

After all 6 modules: sort findings by CVSS score descending, present the full report, then enter the remediation loop.

| # | Module file | Domain | Remediation file |
|---|---|---|---|
| 1 | `modules/network.md` | Interfaces, ports, connections, protocols, Wi-Fi | `remediation/network-fixes.md` |
| 2 | `modules/authentication.md` | NTLM, accounts, password policy, credential guard | `remediation/auth-fixes.md` |
| 3 | `modules/services.md` | Running services, unquoted paths, weak ACLs | `remediation/services-fixes.md` |
| 4 | `modules/remote-access.md` | RDP, WinRM, SSH, WMI | `remediation/remote-access-fixes.md` |
| 5 | `modules/persistence.md` | Scheduled tasks, autoruns, WMI subscriptions | `remediation/persistence-fixes.md` |
| 6 | `modules/patching.md` | Windows Update, Defender, runtime versions | `remediation/patching-fixes.md` |

## CVSS v3.1 Scoring Rubric

| Factor | Value | Weight |
|---|---|---|
| **Attack Vector** | Network / Adjacent / Local / Physical | 0.85 / 0.62 / 0.55 / 0.20 |
| **Attack Complexity** | Low / High | 0.77 / 0.44 |
| **Privileges Required** | None / Low / High | 0.85 / 0.62 / 0.27 |
| **User Interaction** | None / Required | 0.85 / 0.62 |
| **Confidentiality** | High / Low / None | 0.56 / 0.22 / 0.00 |
| **Integrity** | High / Low / None | 0.56 / 0.22 / 0.00 |
| **Availability** | High / Low / None | 0.56 / 0.22 / 0.00 |

Score bands: 9.0–10.0 Critical · 7.0–8.9 High · 4.0–6.9 Medium · 0.1–3.9 Low · 0.0 Info

## Report Format

```
═══════════════════════════════════════════════════
  NETWORK SECURITY AUDIT — <hostname>
  <date>  |  Modules: 6  |  Findings: <n>
═══════════════════════════════════════════════════
EXECUTIVE SUMMARY
  Critical : <n>   High : <n>   Medium : <n>   Low : <n>
  Total exposure score: <sum>

─── CRITICAL ────────────────────────────────────────
[9.8] SMBv1 Enabled                          (network)
  SMBv1 is vulnerable to EternalBlue/WannaCry.
  Vector: AV:N/AC:L/PR:N/UI:N/C:H/I:H/A:H
  Fix available: yes
```

List all findings grouped by severity band, ordered by score descending within each band.

## Remediation Loop

After the full report, work through findings Critical → High → Medium → Low.

For each finding:
1. Display: title, score, and exact fix command from the remediation file listed in the Audit Sequence table above for that module
2. Prompt: `Apply this fix? [yes / no / skip-severity / stop]`
   - `yes` → run command, report success/error, continue
   - `no` → skip, continue
   - `skip-severity` → skip all remaining at this severity level
   - `stop` → exit, show summary
3. For any finding tagged **⚠ DESTRUCTIVE** in the remediation file, add: `⚠ This will affect running services/auth. Confirm? [yes / no]`
4. Never retry a failed command — report error and move on

End with:
```
Remediation complete.
  Fixed   : <n>  (CVSS reduced by <x> pts)
  Skipped : <n>  (scores: <list> — still open)
  Failed  : <n>  (see errors above)
  Remaining exposure score: <sum>
```
