# Error Handling Remediation

Tag a fix **⚠ BEHAVIOR CHANGE** when users or callers get different results for inputs that already worked. **Test:** lines apply only when the baseline test command ran at least one test, and tests use the repo's existing framework and naming.

---

### Swallowed error that leaves state broken

**⚠ BEHAVIOR CHANGE**: code after the failure stops instead of continuing with broken state.

```python
try:
    await db.execute(MIGRATION_SQL)
except Exception:
    log.exception("Migration failed")
    raise
```

**Test:** patch the wrapped call to raise and assert the error is logged and re-raised.
**Verify:** `python -m py_compile <file>`, then the new test.

---

### Swallowed error with a deliberate fallback

**⚠ BEHAVIOR CHANGE**: exception types the fallback was not meant for now propagate.

Catch only the exception type the fallback exists for.

```python
try:
    await message.delete()
except discord.HTTPException:
    pass
```

**Verify:** `python -m py_compile <file>`, then the baseline test command.

---

### Error logged without a traceback

```python
except Exception:
    log.error("Cleanup failed for %s", path, exc_info=True)
```

**Verify:** `python -m py_compile <file>`.

---

### Bare except

```python
except Exception:
```

**Verify:** `python -m flake8 --select=E722 <file>` prints nothing, then the baseline test command.

---

### Discarded task

Keep a reference until the task finishes.

```python
self._tasks = set()  # in __init__

task = asyncio.create_task(self.process(item))
self._tasks.add(task)
task.add_done_callback(self._tasks.discard)
```

Module-level code uses a module-level set the same way.

**Test:** none practical, because garbage collection timing is not deterministic.
**Verify:** `python -m py_compile <file>`, then the baseline test command.

---

### Empty catch block

Log with the injected logger. Add `throw;` when the caller must know; that addition is a **⚠ BEHAVIOR CHANGE** because callers now see the exception.

```csharp
catch (Exception ex)
{
    _logger.LogError(ex, "Refresh failed for {Source}", source);
    throw;
}
```

**Verify:** `dotnet build`, then `dotnet test`.

---

### async void method

**⚠ BEHAVIOR CHANGE**: callers now await the method, so the code after the call runs later.

```csharp
private async Task SaveAsync()
{
    await Store.SaveAsync(Model);
}
```

Event handlers stay `async void` with the whole body inside a try/catch that logs.

**Test:** an xUnit test that awaits the method with a failing dependency and asserts the exception reaches the caller.
**Verify:** `dotnet build`, then `dotnet test --filter <new test name>`.
