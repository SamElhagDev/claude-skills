# Performance Module

## Data Collection (run all in parallel)

### Python
- `py_checks.py` lines for module `performance`: `IMPORT-IN-FUNCTION`, `DB-IN-LOOP`, `GROWS-ONLY`
- Grep (glob `*.py`, 2 lines of context): `argsort\(|sorted\(`, then read for a slice that keeps only the first few items

### .NET
- Grep (globs `*.cs`, `*.razor`): `foreach\s*\(|for\s*\(`, then read loop bodies for EF queries such as `await _db.`
- Grep (globs `*.cs`, `*.razor`, multiline): `\.ToList(Async)?\(\)\s*\.\s*Where\(`

## Risk Indicators

| Finding | Condition | Vector | Score |
|---|---|---|---|
| Per-call work on a hot path | `IMPORT-IN-FUNCTION` or other setup repeated inside code that runs per message, frame or request | degrades / normal use / whole app | 4.0 Medium |
| Import in a rarely called function | `IMPORT-IN-FUNCTION` in a command, startup or error path | maintainability / rare / one feature | 0.6 Low |
| Query per loop iteration | `DB-IN-LOOP` or an EF query in a loop over a collection that grows with users or data | degrades / conditions / one feature | 2.8 Low |
| Stale entries never removed | `GROWS-ONLY` where entries for deleted source data stay behind and are still used | breaks / normal use / one feature | 6.2 Medium |
| Unbounded growth | `GROWS-ONLY` keyed by users, messages or events in a long-running process | degrades / normal use / whole app | 4.0 Medium |
| Full sort for the top few | Sorting a collection that can be large, then keeping only the first few items | degrades / normal use / one feature | 3.5 Low |
| Filtering after loading everything | `.ToList()` before `.Where(` on an EF query | degrades / normal use / one feature | 3.5 Low |

## Analysis Notes

**Hot path:** DiscordVoiceDatabase's `_PerUserPCMSink.write()` imported from `discord.ext.voice_recv.rtp` on every Opus frame, about 50 times a second per speaking user.

**Imports inside functions** are fine in commands and startup code, and are sometimes there to break a circular import. Check before hoisting.

**Stale entries:** DiscordServerAudit's in-memory vector index kept vectors after their message rows were pruned, so searches could return deleted context while memory kept growing.

**Unbounded growth:** the bots run for weeks without restarting, so a dict keyed by user or message needs eviction or cleanup on a lifecycle event.

**Top few:** `np.argsort` over every vector to keep 10 results is O(N log N); `np.argpartition` or `heapq.nlargest` is O(N).

**EF queries:** `.ToList()` pulls every row into memory before the filter runs.
