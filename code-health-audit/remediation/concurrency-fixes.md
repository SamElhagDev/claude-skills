# Concurrency Remediation

Tag a fix **⚠ BEHAVIOR CHANGE** when users or callers get different results for inputs that already worked. **Test:** lines apply only when the baseline test command ran at least one test, and tests use the repo's existing framework and naming.

---

### Blocking call on a hot path

**⚠ BEHAVIOR CHANGE**: other coroutines can run while the work happens on a thread.

```python
pcm_path = await asyncio.to_thread(stream.flush_to_disk)
```

When other threads also touch the data the function reads, guard it with a `threading.Lock`.

**Test:** patch the blocking function to record `threading.get_ident()`, run the coroutine, and assert the function ran on a different thread from the event loop.
**Verify:** `python -m py_compile <file>`, then the new test.

---

### Occasional blocking call

**⚠ BEHAVIOR CHANGE**: other coroutines can run while the work happens on a thread.

```python
schema = await asyncio.to_thread(Path(SCHEMA_PATH).read_text)
```

**Verify:** `python -m py_compile <file>`, then the baseline test command.

---

### Unsynchronized shared state

Hold one `asyncio.Lock` per resource across the whole read-modify-write. Create `self._locks = {}` in `__init__`.

```python
def _playback_lock(self, guild_id):
    return self._locks.setdefault(guild_id, asyncio.Lock())

async def play(self, guild, clip):
    async with self._playback_lock(guild.id):
        await self._play_locked(guild, clip)
```

**Test:** start two calls for the same resource with `asyncio.gather` and assert the invariant holds, for example that only one playback is active at a time.
**Verify:** `python -m py_compile <file>`, then the new test.

---

### Sync-over-async

**⚠ BEHAVIOR CHANGE**: the method and its callers become async.

```csharp
var results = await _service.LoadAsync(ct);
```

Change each caller in the chain to `async Task` and await it.

**Test:** none practical, because thread-pool starvation does not reproduce reliably in a unit test.
**Verify:** `dotnet build`, then `dotnet test`.

---

### Unawaited task

**⚠ BEHAVIOR CHANGE** when the fix adds `await`: the next step now waits for the task.

```csharp
await _cache.RefreshAsync(ct);
```

For fire-and-forget that is intended, make sure failures are logged:

```csharp
_ = RefreshInBackgroundAsync();

private async Task RefreshInBackgroundAsync()
{
    try { await _cache.RefreshAsync(CancellationToken.None); }
    catch (Exception ex) { _logger.LogError(ex, "Background refresh failed"); }
}
```

**Test:** an xUnit test that makes the task fail and asserts the caller sees the failure when awaited, or that the error is logged for fire-and-forget.
**Verify:** `dotnet build`, then `dotnet test --filter <new test name>`.

---

### Writable static state

**⚠ BEHAVIOR CHANGE**: data every user shared becomes per user or per request.

```csharp
builder.Services.AddScoped<SelectionState>();

public sealed class SelectionState
{
    public string? SourceKey { get; set; }
}
```

**Test:** an xUnit test that resolves the service from two scopes and asserts a value set in one scope is not visible in the other.
**Verify:** `dotnet build`, then `dotnet test --filter <new test name>`.
