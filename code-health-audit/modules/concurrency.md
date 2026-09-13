# Concurrency Module

## Data Collection (run all in parallel)

### Python
- `py_checks.py` lines for module `concurrency`: `BLOCKING-IN-ASYNC`
- While reading flagged regions and entry points: module-level or `self.` state that more than one handler or task changes, with an `await` between reading and writing it

### .NET
- Grep (globs `*.cs`, `*.razor`): `\.Result\b|\.Wait\(\)|GetAwaiter\(\)\.GetResult\(\)`
- `dotnet build -nologo -clp:NoSummary`: keep lines containing `warning CS4014`
- Grep (glob `*.cs`): `\bstatic\b`, then read the matching field declarations that have neither `readonly` nor `const`

## Risk Indicators

| Finding | Condition | Vector | Score |
|---|---|---|---|
| Blocking call on a hot path | `BLOCKING-IN-ASYNC` in code that runs during normal operation (per message, audio frame or rotation) and can take more than a few milliseconds | outage / normal use / whole app | 10.0 Critical |
| Occasional blocking call | `BLOCKING-IN-ASYNC` that runs rarely or on small data, such as startup or deleting a few files | degrades / rare / whole app | 2.6 Low |
| Unsynchronized shared state | State changed by several handlers or tasks with an `await` between read and write, and no lock | breaks / conditions / one feature | 4.9 Medium |
| Sync-over-async | `.Result`, `.Wait()` or `GetAwaiter().GetResult()` on a request or Blazor Server path | outage / conditions / whole app | 8.0 High |
| Unawaited task | CS4014 where the ignored task can fail or must finish before the next step | breaks / conditions / one feature | 4.9 Medium |
| Writable static state | A static field without `readonly` or `const` holding per-user or per-request data in a Blazor Server or ASP.NET app | data exposure / conditions / whole app | 8.0 High |

## Analysis Notes

**Hot path:** judge by call frequency and data size. DiscordVoiceDatabase's `_rotate_user()` called `stream.flush_to_disk()`, which wrote about 11.5 MB per speaking user per rotation on the event loop. The gateway heartbeat stalled and the bot went grey: Critical. `open()` inside `_init_schema()` at startup is an Occasional blocking call.

**How far py_checks looks:** it follows one level into repo functions. Deeper chains show up while reading the flagged function.

**Shared state:** discord.py handlers and `tasks.loop` bodies interleave at every `await`, so a read-modify-write across an `await` can lose updates, for example two playback requests for the same guild.

**Sync-over-async:** each blocked call holds a thread-pool thread; under load the app stops responding.

**Static state:** a static field is shared by every user and circuit. A deliberate process-wide guard such as usvotemap's `static readonly SemaphoreSlim _gate` is not a finding.
