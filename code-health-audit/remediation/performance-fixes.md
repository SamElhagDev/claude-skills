# Performance Remediation

Tag a fix **⚠ BEHAVIOR CHANGE** when users or callers get different results for inputs that already worked. **Test:** lines apply only when the baseline test command ran at least one test, and tests use the repo's existing framework and naming.

---

### Per-call work on a hot path

Move the import or setup to module scope or `__init__`.

```python
from discord.ext.voice_recv.rtp import FakePacket, SilencePacket


class _PerUserPCMSink:
    def write(self, user, data):
        if isinstance(data.packet, (SilencePacket, FakePacket)):
            return
```

**Verify:** `python -m py_compile <file>`; import the module (for example `python -c "import recording.recorder"`) to confirm no circular import; then the baseline test command.

---

### Import in a rarely called function

Hoist the import only when that creates no circular import; otherwise report the finding with `Fix available: no`.

**Verify:** import the module with `python -c "import <module>"`, then the baseline test command.

---

### Query per loop iteration

Load everything the loop needs with one query, then group in memory.

```python
placeholders = ",".join("?" * len(poll_ids))
cursor = await conn.execute(f"SELECT * FROM votes WHERE poll_id IN ({placeholders})", poll_ids)
votes_by_poll = {}
for row in await cursor.fetchall():
    votes_by_poll.setdefault(row["poll_id"], []).append(row)
```

**Verify:** `python -m py_compile <file>`, then the baseline test command.

---

### Stale entries never removed

**⚠ BEHAVIOR CHANGE**: results no longer include entries for deleted data.

Remove entries in the same place the source data is deleted.

```python
deleted_ids = await db.prune_context(cutoff)
self.index.remove(deleted_ids)
```

**Test:** add entries, delete their source rows through the normal path, and assert a search no longer returns them.
**Verify:** `python -m py_compile <file>`, then the new test.

---

### Unbounded growth

**⚠ BEHAVIOR CHANGE**: the oldest entries are evicted.

```python
from collections import OrderedDict


class RecentCache:
    def __init__(self, limit=1000):
        self._items = OrderedDict()
        self._limit = limit

    def remember(self, key, value):
        self._items[key] = value
        self._items.move_to_end(key)
        if len(self._items) > self._limit:
            self._items.popitem(last=False)
```

Deleting entries on the matching lifecycle event (a user leaves, a poll closes) also works.

**Verify:** `python -m py_compile <file>`, then the baseline test command.

---

### Full sort for the top few

```python
k = min(k, len(scores))
top = np.argpartition(-scores, k - 1)[:k]
top = top[np.argsort(-scores[top])]
```

When scores can tie, the order of tied items can differ from the full sort.

**Verify:** `python -m py_compile <file>`; compare old and new results on at least 1000 random inputs, including ties; then the baseline test command.

---

### Filtering after loading everything

Filter before the query runs.

```csharp
var rows = await _db.Datasets.Where(d => d.IsPublished).ToListAsync(ct);
```

When the filter compares strings, check case sensitivity: the database collation can differ from C# string comparison.

**Verify:** `dotnet build`, then `dotnet test`.
