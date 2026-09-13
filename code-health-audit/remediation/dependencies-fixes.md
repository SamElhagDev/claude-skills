# Dependencies Remediation

Tag a fix **⚠ BEHAVIOR CHANGE** when users or callers get different results for inputs that already worked. **Test:** lines apply only when the baseline test command ran at least one test, and tests use the repo's existing framework and naming.

---

### Unpinned requirements

**⚠ BEHAVIOR CHANGE**: deploys install these exact versions and stop picking up new releases.

Pin every line to the version `python -m pip freeze` reports. For example:

```text
discord.py[voice]==2.7.1
aiosqlite==0.21.0
```

**Test:** none practical; the check below proves the pins.
**Verify:** rerun `py_checks.py` for the repo and confirm there is no `UNPINNED-DEP` line.

---

### Undeclared dependency

Add the package with the installed version, for example `numpy==2.2.6`.

**Test:** none practical; the check below proves the declaration.
**Verify:** rerun `py_checks.py` and confirm the `UNDECLARED-DEP` line for that import is gone.

---

### Vulnerable package

**⚠ BEHAVIOR CHANGE**: a library version changes.

Upgrade the direct package to a fixed version, or reference the vulnerable transitive package explicitly at a fixed version.

```xml
<PackageReference Include="MimeKit" Version="4.15.1" />
```

**Test:** none practical; the vulnerability report below proves the upgrade.
**Verify:** `dotnet list package --vulnerable --include-transitive` no longer lists the package, then `dotnet build` and `dotnet test`.
