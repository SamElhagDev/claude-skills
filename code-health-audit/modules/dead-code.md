# Dead Code Module

## Data Collection (run all in parallel)

### Python
- `python -m flake8 --select=F401,F811,F841 .`
- `py_checks.py` lines for module `dead-code`: `UNUSED-OPTIONAL-PARAM`, `UNREFERENCED-FUNC`

### .NET
- `dotnet build -nologo -clp:NoSummary`: keep lines containing `warning CS0168`, `warning CS0219` or `warning CS0162`
- Grep (glob `*.cs`): `private\s+(static\s+)?(async\s+)?[\w<>\[\],?.]+\s+(\w+)\s*\(`; Grep the repo for each method name and keep names found only at their declaration

## Risk Indicators

| Finding | Condition | Vector | Score |
|---|---|---|---|
| Unused imports or variables | F401, F841, F811 on an import, CS0168 or CS0219, grouped one finding per file | maintainability / normal use / one user | 0.8 Low |
| Name redefined before use | F811 on a function or method | breaks / normal use / one feature | 6.2 Medium |
| Optional parameter never passed | `UNUSED-OPTIONAL-PARAM` confirmed by reading | maintainability / future change / one feature | 0.5 Low |
| Function never referenced | `UNREFERENCED-FUNC` confirmed by reading | maintainability / future change / one feature | 0.5 Low |
| Unreachable code | CS0162, grouped one finding per file | maintainability / normal use / one user | 0.8 Low |
| Private member never referenced | A private method found only at its declaration | maintainability / future change / one feature | 0.5 Low |

## Analysis Notes

**Imports kept for side effects** (a module imported so its import-time code runs, or re-exported from `__init__.py`) are not unused.

**Not dead:** discord.py commands, listeners and views registered through decorators or `add_view`; functions named in strings for `getattr`; public functions another repo imports.

**F811 on a function:** the later definition silently replaces the earlier one, so decide which behavior is intended before deleting either.

**Optional parameters:** DiscordServerAudit's `VectorIndex.search()` kept an `allowed_ids` parameter no caller passed, and its filter branch blocked a faster top-k rewrite.
