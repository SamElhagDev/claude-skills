# Duplication Remediation

Tag a fix **⚠ BEHAVIOR CHANGE** when users or callers get different results for inputs that already worked. **Test:** lines apply only when the baseline test command ran at least one test, and tests use the repo's existing framework and naming.

---

### Default copied into several call sites

Put one accessor in the module that owns the setting and route every call site through it. When the copies currently disagree, this is a **⚠ BEHAVIOR CHANGE**: the accessor's value wins everywhere.

```python
def model_name() -> str:
    return config.get("factcheck.context.semantic.model", "gemini-embedding-001")
```

**Test:** patch `model_name` to return a sentinel and assert every consumer receives the sentinel.
**Verify:** `python -m py_compile <files>`, then the new test.

---

### Cosmetic default copied

Move the default into one constant or accessor and use it at every call site.

**Verify:** `python -m py_compile <files>`.

---

### Copies that have drifted apart

**⚠ BEHAVIOR CHANGE**: copies that lacked a fix now behave like the most correct copy.

Extract one helper from the most correct copy and call it from each site.

```python
def _ranked_lines(rows, limit):
    lines = []
    for i, row in enumerate(rows[:limit]):
        medal = MEDALS[i] if i < len(MEDALS) else f"{i + 1}."
        lines.append(f"{medal} {row['name']}: {row['votes']}")
    return lines
```

**Test:** send the input the drifted copy handled wrong (for the medal loop, more rows than medals) through each call site.
**Verify:** `python -m py_compile <files>`, then the new test.

---

### Identical copies

Extract one helper and call it from each site.

```python
def _row_to_vote(row):
    vote = dict(row)
    vote["choices"] = json.loads(vote["choices"])
    return vote
```

**Verify:** `python -m py_compile <files>`, then the baseline test command.

---

### Existing helper not used

Replace the repeated code with a call to the helper. When the helper behaves differently from the repeated code, this is a **⚠ BEHAVIOR CHANGE**.

```python
return [_row_to_vote(row) for row in rows]
```

**Verify:** `python -m py_compile <files>`, then the baseline test command.
