# Plan: Review High-Risk Transitive Dependencies [SEC][SUPPLY][P2]

## Summary

- Identify single-maintainer packages in critical dependency paths (auth, crypto, build)
- Flag packages with low download counts or suspicious patterns
- Document findings with risk assessment
- Recommend mitigations (pin, fork, or replace)

## Implementation Steps

1. **Extract critical dependency trees**
   - Run: `npm ls --all --json > npm-deps-tree.json` (frontend)
   - Run: `uv pip compile --generate-hashes` to inspect Python deps
   - Focus paths: `supertokens-*`, `stripe`, `@anthropic-ai/*`, crypto libs

2. **Analyze npm dependencies for risk signals**
   - Script: `scripts/audit_npm_deps.py`
   - Check via npm registry API:
     - Maintainer count (`maintainers` array length)
     - Weekly downloads (flag if < 10K for critical path)
     - Last publish date (flag if > 2 years)
     - Repository existence and activity
   - Filter to: auth, crypto, SSE, API client packages

3. **Analyze Python dependencies for risk signals**
   - Script: `scripts/audit_python_deps.py`
   - Check via PyPI JSON API:
     - Author/maintainer metadata
     - Download stats via pypistats
     - Last release date
   - Focus: `supertokens-python`, `anthropic`, `stripe`, `pyjwt`, `cryptography`

4. **Cross-reference with known-good lists**
   - OpenSSF Scorecard for major packages
   - Check if package is in npm/PyPA advisory databases
   - Compare against CNCF/OpenJS Foundation projects

5. **Generate risk report**
   - Output: `audits/reports/supply-chain-review.report.md`
   - Format:
     - Critical-path packages with single maintainer
     - Packages with low activity signals
     - Recommended actions (accept, pin version, find alternative)

6. **Update CI for ongoing monitoring** (optional stretch)
   - Add `socket.dev` or `deps.dev` integration to PR checks
   - Or add custom script to dependency-review workflow

## Tests

- **Manual validation:**
  - Verify script outputs actionable package list
  - Spot-check 3-5 flagged packages manually on npm/PyPI
  - Confirm critical auth/crypto packages have >1 maintainer

- **No automated tests required:**
  - This is a one-time audit producing a report
  - Future runs via scheduled CI job

## Dependencies & Risks

- **Dependencies:**
  - npm registry API (public, no auth required)
  - PyPI JSON API (public)
  - Optional: pypistats API for download counts

- **Risks/edge cases:**
  - False positives: low-download package may be new but legitimate
  - API rate limits: batch requests, add delays
  - Maintainer count != actual risk (some packages have shadow maintainers)

- **Mitigation:**
  - Manual review of flagged packages before action
  - Document reasoning in report for each flag
  - Focus on critical path only (not all 500+ transitive deps)
