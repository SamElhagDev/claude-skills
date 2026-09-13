# Dependencies Module

## Data Collection (run all in parallel)

### Python
- `py_checks.py` lines for module `dependencies`: `UNPINNED-DEP`, `UNDECLARED-DEP`
- `python -m pip freeze`, for the installed versions to pin to

### .NET
- `dotnet list package --vulnerable --include-transitive` from the repo root; keep rows that show a severity
- When the command fails because restore or the vulnerability feed is unreachable, list "NuGet vulnerability check" under Not checked

## Risk Indicators

| Finding | Condition | Vector | Score |
|---|---|---|---|
| Unpinned requirements | `UNPINNED-DEP` | outage / rare / whole app | 6.5 Medium |
| Undeclared dependency | `UNDECLARED-DEP` confirmed as a real third-party package | outage / conditions / whole app | 8.0 High |
| Vulnerable package (Critical) | Advisory severity Critical | advisory: Critical | 9.5 Critical |
| Vulnerable package (High) | Advisory severity High | advisory: High | 8.0 High |
| Vulnerable package (Moderate) | Advisory severity Moderate | advisory: Moderate | 5.5 Medium |
| Vulnerable package (Low) | Advisory severity Low | advisory: Low | 2.0 Low |

## Analysis Notes

**Pins:** an unpinned requirement lets a new release break the next deploy. DiscordVoiceDatabase pinned all ten of its requirements during its 2026-09-11 audit. Pin to the versions the tests ran against, keeping extras such as `discord.py[voice]`; the deploy server installs from `requirements.txt`, so the pins become the production versions.

**Undeclared imports:** check the import-to-package mapping first. Namespace extensions come from their own package, for example `discord.ext.voice_recv` from `discord-ext-voice-recv`.

**Transitive vulnerabilities:** bytecraft.us got a vulnerable MimeKit through MailKit 4.15.0 and fixed it by adding an explicit MimeKit 4.15.1 reference.
