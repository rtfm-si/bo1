# Plan: Fix Pre-commit Lint Errors

## Summary

- Fix 23 Ruff lint errors blocking pre-commit
- 19 auto-fixable with `--fix`, 4 require manual review
- Issues in `bo1/graph/routers/__init__.py` (E402) and `bo1/prompts/__init__.py` (F401)

## Implementation Steps

1. Run `ruff check --fix` to auto-fix 19 errors
2. Review `bo1/graph/routers/__init__.py` E402 errors (module imports not at top)
   - Restructure imports to comply with E402 or add appropriate `# noqa` if intentional
3. Review `bo1/prompts/__init__.py` F401 error (unused import CORE_PROTOCOL)
   - Add to `__all__` if intended for re-export, or remove if unused
4. Run `make pre-commit` to verify all errors resolved
5. Verify test suite passes after fixes

## Tests

- Unit tests: `make test` - ensure no regressions
- Integration: `make pre-commit` - must pass cleanly
- Manual validation: None required

## Dependencies & Risks

- Dependencies: None
- Risks: Auto-fix may change import order; verify no circular import issues

---

Ready for implementation.
