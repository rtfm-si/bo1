# Supply Chain Security Review Report

**Generated:** 2025-12-12
**Scope:** High-risk transitive dependencies in critical paths (auth, crypto, build)

## Executive Summary

| Category | Analyzed | Flagged | Critical |
|----------|----------|---------|----------|
| npm packages | 70 | 10 | 0 |
| Python packages | 16 | 12 | 0 |

**Overall Risk: LOW-MEDIUM**

No critical supply-chain vulnerabilities detected. Most flags are informational (single-maintainer on popular packages, missing PyPI metadata). Key auth/crypto packages are well-maintained by reputable organizations.

---

## npm Dependency Analysis

### High-Risk Findings

| Package | Maintainers | Downloads/wk | Last Publish | Risk Signals |
|---------|-------------|--------------|--------------|--------------|
| @types/marked | 1 (types) | N/A | 800d | STALE, SINGLE_MAINTAINER |
| js-cookie | 2 | 16.2M | 845d | STALE |

**Recommendations:**
- `@types/marked`: Accept risk - types-only package, marked itself is active
- `js-cookie`: Monitor for security patches; consider `cookie` (native) as alternative if actively developed

### Medium-Risk Findings

| Package | Maintainers | Downloads/wk | Risk Signals |
|---------|-------------|--------------|--------------|
| dompurify | 1 (cure53) | 16.8M | SINGLE_MAINTAINER |
| isomorphic-dompurify | 1 (kkomelin) | N/A | SINGLE_MAINTAINER |
| set-cookie-parser | 1 (nfriedly) | 14.8M | SINGLE_MAINTAINER |
| lucide-svelte | 1 (ericfennis) | 132K | SINGLE_MAINTAINER |
| svelte-dnd-action | 1 (isaac_hagoel) | 48K | SINGLE_MAINTAINER |

**Assessment:**
- `dompurify`: **ACCEPT** - Cure53 is a renowned security firm; this is THE standard XSS sanitization library
- `isomorphic-dompurify`: **ACCEPT** - Thin wrapper around dompurify for SSR
- `set-cookie-parser`: **ACCEPT** - 14.8M downloads/week, used by SvelteKit core
- `lucide-svelte`: **ACCEPT** - Community Svelte bindings for Lucide icons (popular, low-risk surface)
- `svelte-dnd-action`: **MONITOR** - Lower download count; pin version, review updates manually

### Low-Risk Findings (Informational)

| Package | Issue | Assessment |
|---------|-------|------------|
| @types/cookie | Single maintainer (DefinitelyTyped) | Accept - DT bot account |
| @types/dompurify | Single maintainer | Accept - DT bot account |
| @types/js-cookie | Single maintainer | Accept - DT bot account |

---

## Python Dependency Analysis

### Critical Path Packages - Assessment

| Package | Downloads/mo | Last Release | Maintainer | Risk | Action |
|---------|--------------|--------------|------------|------|--------|
| cryptography | 610M | 57d | PyCA | LOW | ACCEPT |
| pyjwt | 307M | 379d | (unlisted) | LOW | ACCEPT |
| anthropic | 35M | 17d | Anthropic | LOW | ACCEPT |
| stripe | 16M | 7d | Stripe | LOW | ACCEPT |
| supertokens-python | 61K | 111d | SuperTokens | LOW | ACCEPT |

**Note:** Python packages often don't list maintainer info in PyPI metadata - this is a metadata issue, not a risk signal. All critical packages above are:
- Maintained by reputable organizations (PyCA, Anthropic, Stripe, SuperTokens)
- Have high download counts indicating wide ecosystem adoption
- Have recent releases indicating active maintenance

### Framework Packages

| Package | Downloads/mo | Last Release | Risk |
|---------|--------------|--------------|------|
| fastapi | 227M | 1d | LOW |
| langchain | 97M | 3d | LOW |
| langchain-core | 77M | 2d | LOW |
| langgraph | 23M | 16d | LOW |
| sqlalchemy | 248M | 1d | LOW |
| alembic | 114M | 27d | LOW |
| httpx | 315M | 87d | LOW |
| aiohttp | 288M | 44d | LOW |
| redis | 119M | 22d | LOW |
| boto3 | 1.4B | recent | LOW |

All framework dependencies are high-download, actively maintained packages from established organizations.

---

## Mitigation Status

### Already Implemented

- [x] npm dependency versions pinned (no `^` ranges)
- [x] OSV-Scanner in CI for malware/typosquatting detection
- [x] `npm audit` failures blocking in CI
- [x] Dependency review action on PRs

### Recommended Actions

| Priority | Action | Effort | Rationale |
|----------|--------|--------|-----------|
| P3 | Pin `svelte-dnd-action` minor version | 5 min | Lower ecosystem adoption |
| P3 | Document dompurify single-maintainer acceptance | 10 min | Audit trail for Cure53 trust decision |
| P4 | Set up Socket.dev or deps.dev monitoring | 1-2 hr | Proactive supply-chain alerts |

---

## Cross-Reference Results

### OpenSSF Scorecard (spot-check)

| Package | Score | Assessment |
|---------|-------|------------|
| rollup | 7.1/10 | Good |
| svelte | 6.8/10 | Good |
| vite | 7.3/10 | Good |
| fastapi | 6.9/10 | Good |

### Known Vulnerability Databases

- npm advisory: No unpatched advisories in dependencies
- PyPI advisory: No unpatched advisories in dependencies
- OSV Scanner: Clean (integrated in CI)

---

## Conclusion

The dependency supply chain for this project is **healthy**. Critical-path packages (auth, crypto, API clients) are:
1. Maintained by established organizations
2. Have high ecosystem adoption (millions of downloads)
3. Actively maintained with recent releases

The single-maintainer flags are mostly:
- DefinitelyTyped bot accounts (acceptable)
- Specialized packages from security-focused maintainers (dompurify/Cure53)
- Lower-risk UI utilities (icons, drag-and-drop)

**No immediate action required.** Continue monitoring via OSV-Scanner and dependency review on PRs.
