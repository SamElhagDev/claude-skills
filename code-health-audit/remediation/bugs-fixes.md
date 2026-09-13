# Bugs Remediation

Tag a fix **⚠ BEHAVIOR CHANGE** when users or callers get different results for inputs that already worked. A fix that only stops a crash or an error is not tagged. **Test:** lines apply only when the baseline test command ran at least one test, and tests use the repo's existing framework and naming.

---

### Attribute used before it exists

Set the attribute in `__init__`, usually to `None`, and return early where it can be read first.

```python
def __init__(self):
    self.voice_client = None

def stop(self):
    if self.voice_client is None:
        return
    self.voice_client.stop()
```

**Test:** create the object without calling the method that sets the attribute, call the reading method, and assert it does not raise.
**Verify:** `python -m py_compile <file>`, then the new test.

---

### Import-time side effect

Move the effect into a function and call it from the entry point after setup. For logging, call it after handlers are attached.

```python
# config.py
def log_summary():
    log.info("Version: %s", VERSION)

# bot.py, after logging is configured
config.log_summary()
```

**Verify:** `python -m py_compile <files>`, then the baseline test command.

---

### Mutable default argument

**⚠ BEHAVIOR CHANGE**: callers that relied on the shared default now get a fresh object each call.

```python
def collect(vote, seen=None):
    seen = [] if seen is None else seen
```

**Test:** call the function twice without the argument and assert the second call does not see data from the first.
**Verify:** `python -m py_compile <file>`, then the new test.

---

### Discord text over its limit

Send the text through a helper the repo already has; otherwise split it across fields or clip it at the limit.

```python
embeds.add_chunked_field(embed, "Recent Votes", lines, sep="\n")
```

**Test:** run the command with mocked data at the largest realistic size (for `mystats`: 15 entries with 30-character titles and 60-character choices) and assert every field value is at most 1024 characters.
**Verify:** `python -m py_compile <file>`, then the new test.

---

### Naive datetime

**⚠ BEHAVIOR CHANGE**: displayed times move to the chosen timezone.

```python
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

EASTERN = ZoneInfo("America/New_York")
stored = datetime.now(timezone.utc)
shown = stored.astimezone(EASTERN)
```

**Test:** assert the datetime the function returns or formats has `tzinfo` set.
**Verify:** `python -m py_compile <file>`, then the new test.

---

### Nullable dereference

Handle the null case where the value is produced: return early, use `?.` or `??`, or throw with a clear message.

```csharp
var contest = await _db.Contests.FirstOrDefaultAsync(c => c.Id == id, ct);
if (contest is null)
    return null;
```

**Test:** an xUnit test that passes the input producing null and asserts the guarded result.
**Verify:** `dotnet build`, then `dotnet test --filter <new test name>`.

---

### JS interop during prerendering

Move the call to `OnAfterRenderAsync` and run it once.

```csharp
protected override async Task OnAfterRenderAsync(bool firstRender)
{
    if (firstRender)
        await JS.InvokeVoidAsync("siteInterop.init");
}
```

**Test:** a Playwright test that loads the page and asserts the Blazor error UI stays hidden, when the repo has an E2E project; otherwise none practical.
**Verify:** `dotnet build`, then `dotnet test` for the E2E project when one exists.

---

### Event subscription never removed

Implement `IDisposable` and unsubscribe in `Dispose`.

```razor
@implements IDisposable

@code {
    protected override void OnInitialized() => State.Changed += OnStateChanged;
    public void Dispose() => State.Changed -= OnStateChanged;
}
```

**Verify:** `dotnet build`.

---

### HttpClient created per call

Register the factory once and create clients from it.

```csharp
builder.Services.AddHttpClient();

public sealed class FeedService(IHttpClientFactory http)
{
    public Task<string> GetAsync(string url) => http.CreateClient().GetStringAsync(url);
}
```

**Verify:** `dotnet build`, then `dotnet test`.
