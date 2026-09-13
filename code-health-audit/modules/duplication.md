# Duplication Module

## Data Collection (run all in parallel)

### Python
- `py_checks.py` lines for module `duplication`: `DUP-CONFIG-DEFAULT`
- While reading (flagged regions, entry points and config in quick mode; every file in deep mode): three or more near-identical blocks, and code that repeats what a helper in the repo already does

### .NET
- While reading: three or more near-identical blocks, and repeated code a helper already covers

## Risk Indicators

| Finding | Condition | Vector | Score |
|---|---|---|---|
| Default copied into several call sites | `DUP-CONFIG-DEFAULT` where a drifted default would silently change behavior | breaks / future change / one feature | 3.4 Low |
| Cosmetic default copied | `DUP-CONFIG-DEFAULT` where drift would only change a display value | maintainability / future change / one feature | 0.5 Low |
| Copies that have drifted apart | Three or more copies of the same logic where at least one already differs, such as a guard only some copies have | breaks / conditions / one feature | 4.9 Medium |
| Identical copies | Three or more identical copies of the same logic | maintainability / future change / one feature | 0.5 Low |
| Existing helper not used | Code repeats what a helper in the repo already does | maintainability / future change / one feature | 0.5 Low |

## Analysis Notes

**Drifting defaults:** DiscordServerAudit read `factcheck.context.semantic.model` with the default `gemini-embedding-001` in three places. Vectors only load on an exact model and dimension match, so a drifted default would silently load zero vectors.

**Copies:** DiscordServerVote open-coded `dict(row)` plus `json.loads` in five database functions, next to an existing `_row_to_poll` that showed the pattern to follow. Two of three copies of a medal-line loop lacked the bounds check the third had: that is drift.

**Coverage:** quick mode only sees duplication inside the files it reads; "deep audit" finds more.
