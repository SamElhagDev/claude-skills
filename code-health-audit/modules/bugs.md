# Bugs Module

## Data Collection (run all in parallel)

### Python
- `py_checks.py` lines for module `bugs`: `ATTR-OUTSIDE-INIT`, `IMPORT-SIDE-EFFECT`, `MUTABLE-DEFAULT`
- Grep (glob `*.py`, content with line numbers): `add_field\(|Embed\(|set_footer\(|\.send\(|\.edit\(|SelectOption\(`
- Grep (glob `*.py`): `datetime\.(now|utcnow)\(\s*\)`

### .NET
- `dotnet build -nologo -clp:NoSummary`: keep lines containing `warning CS86`
- Grep (globs `*.razor`, `*.cs`): `OnInitialized(Async)?\s*\(`, then read each method for `JS.Invoke`, `JSRuntime.Invoke` or `IJSRuntime`
- Grep (globs `*.razor`, `*.razor.cs`): `\+=\s*[A-Za-z_]`; in those files Grep `IDisposable|IAsyncDisposable`
- Grep (glob `*.cs`): `new HttpClient\(`

## Risk Indicators

| Finding | Condition | Vector | Score |
|---|---|---|---|
| Attribute used before it exists | `ATTR-OUTSIDE-INIT`, and a method that reads the attribute can run before the method that sets it | breaks / conditions / one feature | 4.9 Medium |
| Import-time side effect | `IMPORT-SIDE-EFFECT` whose effect is lost or wrong because of import order | degrades / normal use / whole app | 4.0 Medium |
| Mutable default argument | `MUTABLE-DEFAULT` on a function that changes the argument | breaks / conditions / one feature | 4.9 Medium |
| Discord text over its limit | Text built at runtime can pass a Discord limit with realistic data, with no length check | breaks / conditions / one user | 4.3 Medium |
| Naive datetime | `now()` or `utcnow()` without a timezone in code that shows or compares times | breaks / normal use / one feature | 6.2 Medium |
| Nullable dereference | A CS86xx warning on a value that can be null at runtime | breaks / conditions / one feature | 4.9 Medium |
| JS interop during prerendering | `IJSRuntime` called from `OnInitialized` or `OnInitializedAsync` of a prerendered component | breaks / normal use / one feature | 6.2 Medium |
| Event subscription never removed | `+=` on a longer-lived object's event in a component with no `Dispose` that removes it | degrades / normal use / one feature | 3.5 Low |
| HttpClient created per call | `new HttpClient(` inside a method that runs per request or per call | degrades / conditions / whole app | 3.2 Low |

## Analysis Notes

**Attributes:** attributes set in discord.py `setup_hook`, `cog_load` or `on_ready` and only read afterwards are normal. Report only when a real call order reads first, such as `stop()` before `start()`.

**Import-time effects:** `load_dotenv()` and logger setup are normal. Report when the effect is lost or wrong: `log.info` before handlers exist (the messages vanish), network or file work during import, or work a test triggers just by importing.

**Discord limits:** estimate the largest realistic value from the code, items times characters per item. `>history mystats` built 15 lines of about 105 characters: 1579 characters for a 1024-character field. Prefer a helper the repo already has (`add_chunked_field`, `clip`).

| Object | Limit |
|---|---|
| Message content | 2000 characters |
| Embed title | 256 |
| Embed description | 4096 |
| Fields per embed | 25 |
| Field name / field value | 256 / 1024 |
| Footer text | 2048 |
| All embed text in one message | 6000 |
| Embeds per message | 10 |
| Select menu options | 25; label, value and description up to 100 each |
| Button label | 80 |

**Datetimes:** the user's bots show US Eastern time. A naive `now()` is only correct when the server's clock happens to use that timezone.

**Nullable warnings:** report only when the value can really be null, for example after `FirstOrDefault`, not when the compiler cannot see an assignment that always happens.

**Prerendering:** interactive render modes prerender by default, and JS interop is not available while prerendering. It belongs in `OnAfterRenderAsync(firstRender)`.

**Subscriptions:** a component that subscribes to an event on a singleton or scoped service stays in memory after navigation until it unsubscribes.

**HttpClient:** a new client per call exhausts sockets under load. `IHttpClientFactory` or an injected client reuses connections.
