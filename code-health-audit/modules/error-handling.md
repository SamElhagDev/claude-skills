# Error Handling Module

## Data Collection (run all in parallel)

### Python
- `py_checks.py` lines for module `error-handling`: `EXCEPT-SWALLOW`, `EXCEPT-NO-TRACEBACK`, `TASK-UNSTORED`
- `python -m flake8 --select=E722 .`

### .NET
- Grep (globs `*.cs`, `*.razor`, multiline): `catch\s*(\([^)]*\))?\s*\{\s*\}`
- Grep (globs `*.cs`, `*.razor`): `catch\s*\(\s*Exception`, then read each block for a log call or `throw`
- Grep (globs `*.cs`, `*.razor`): `async\s+void\s+\w+\s*\(`

## Risk Indicators

| Finding | Condition | Vector | Score |
|---|---|---|---|
| Swallowed error that leaves state broken | `EXCEPT-SWALLOW` where later code relies on what the try block was supposed to do | breaks / conditions / one feature | 4.9 Medium |
| Swallowed error with a deliberate fallback | `EXCEPT-SWALLOW` where skipping is intended but the exception type is broad | maintainability / conditions / one feature | 0.7 Low |
| Error logged without a traceback | `EXCEPT-NO-TRACEBACK` in code that runs unattended: loops, tasks, workers | degrades / conditions / one feature | 2.8 Low |
| Bare except | flake8 E722 | degrades / conditions / one feature | 2.8 Low |
| Discarded task | `TASK-UNSTORED` for a task that does real work | breaks / rare / one feature | 4.0 Medium |
| Empty catch block | An empty `catch`, or a catch-all that neither logs nor rethrows | degrades / conditions / one feature | 2.8 Low |
| async void method | `async void` that is not an event handler | breaks / conditions / one user | 4.3 Medium |

## Analysis Notes

**Narrow handlers are intentional.** `except discord.HTTPException: pass` around a best-effort delete is fine; `py_checks.py` only reports broad handlers.

**Broken state:** a swallowed error leaves state broken when code after the try uses its result, such as a startup migration, a file that is written and then read, or a message that is edited and then referenced. DiscordVoiceDatabase's migration loop in `bot.py` was `except Exception: pass`.

**Unattended code:** `tasks.loop` bodies, queue workers and cleanup jobs run with nobody watching. A traceback in the log is often the only evidence a failure leaves.

**Discarded tasks:** the event loop keeps only a weak reference to a task, so a task nothing references can be garbage-collected before it finishes, and its exception is never seen.

**async void in C#:** callers cannot catch its exceptions, and in Blazor Server an unhandled exception ends that user's circuit. Real event handlers (`object sender, EventArgs e`) stay `async void` with a try/catch inside.
