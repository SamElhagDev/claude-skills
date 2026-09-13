# Dead Code Remediation

Tag a fix **⚠ BEHAVIOR CHANGE** when users or callers get different results for inputs that already worked. **Test:** lines apply only when the baseline test command ran at least one test, and tests use the repo's existing framework and naming.

---

### Unused imports or variables

Delete the import. For F841, keep the call when it has side effects and drop only the assignment.

```python
await channel.send(embed=embed)
```

**Verify:** `python -m flake8 --select=F401,F841 <file>` prints nothing, `python -m py_compile <file>`, then the baseline test command.

---

### Name redefined before use

**⚠ BEHAVIOR CHANGE**: the definition that was silently replaced either comes back or goes away.

Keep the intended definition and rename or delete the other one.

**Test:** call the name and assert the intended behavior.
**Verify:** `python -m flake8 --select=F811 <file>` prints nothing, then the new test.

---

### Optional parameter never passed

Remove the parameter and the code that only ran when it was passed.

```python
def search(self, query_vec, k=10):
```

**Verify:** `python -m py_compile <file>`, then the baseline test command.

---

### Function never referenced

Delete the function.

**Verify:** Grep the repo for the name and find no matches, `python -m py_compile <file>`, then the baseline test command.

---

### Unreachable code

Delete the unreachable statements.

**Verify:** `dotnet build` shows no CS0162 for the file, then `dotnet test`.

---

### Private member never referenced

Delete the member.

**Verify:** `dotnet build`, then `dotnet test`.
