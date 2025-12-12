#!/usr/bin/env python3
"""Audit npm dependencies for supply-chain risk signals.

Checks critical-path packages for:
- Maintainer count (flag if single maintainer)
- Weekly downloads (flag if < 10K for critical path)
- Last publish date (flag if > 2 years stale)
- Repository existence
"""

import argparse
import json
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import urlopen

# Critical-path package prefixes/names to analyze
CRITICAL_PATTERNS = [
    "supertokens",
    "svelte",
    "vite",
    "rollup",
    "tailwind",
    "cookie",
    "marked",
    "dompurify",
    "js-cookie",
]

# Risk thresholds
MIN_DOWNLOADS_CRITICAL = 10_000  # Weekly downloads
MAX_STALE_DAYS = 730  # 2 years
MIN_MAINTAINERS = 2


def fetch_npm_info(package_name: str) -> dict[str, Any] | None:
    """Fetch package info from npm registry."""
    url = f"https://registry.npmjs.org/{package_name}"
    try:
        with urlopen(url, timeout=10) as resp:  # noqa: S310 - URL is hardcoded https
            return json.loads(resp.read().decode())
    except (URLError, HTTPError) as e:
        print(f"  Warning: Could not fetch {package_name}: {e}", file=sys.stderr)
        return None


def fetch_npm_downloads(package_name: str) -> int | None:
    """Fetch weekly download count from npm."""
    url = f"https://api.npmjs.org/downloads/point/last-week/{package_name}"
    try:
        with urlopen(url, timeout=10) as resp:  # noqa: S310 - URL is hardcoded https
            data = json.loads(resp.read().decode())
            return data.get("downloads")
    except (URLError, HTTPError):
        return None


def analyze_package(name: str) -> dict[str, Any]:
    """Analyze a single npm package for risk signals."""
    result = {
        "name": name,
        "maintainers": None,
        "maintainer_count": None,
        "weekly_downloads": None,
        "last_publish": None,
        "days_since_publish": None,
        "repository": None,
        "risks": [],
    }

    info = fetch_npm_info(name)
    if not info:
        result["risks"].append("FETCH_FAILED")
        return result

    # Maintainers
    maintainers = info.get("maintainers", [])
    result["maintainers"] = [m.get("name") for m in maintainers]
    result["maintainer_count"] = len(maintainers)
    if len(maintainers) < MIN_MAINTAINERS:
        result["risks"].append(f"SINGLE_MAINTAINER ({len(maintainers)})")

    # Last publish date
    time_info = info.get("time", {})
    modified = time_info.get("modified")
    if modified:
        try:
            mod_dt = datetime.fromisoformat(modified.replace("Z", "+00:00"))
            result["last_publish"] = modified
            days_old = (datetime.now(UTC) - mod_dt).days
            result["days_since_publish"] = days_old
            if days_old > MAX_STALE_DAYS:
                result["risks"].append(f"STALE ({days_old} days)")
        except ValueError:
            pass

    # Repository
    repo = info.get("repository", {})
    if isinstance(repo, dict):
        result["repository"] = repo.get("url")
    elif isinstance(repo, str):
        result["repository"] = repo
    if not result["repository"]:
        result["risks"].append("NO_REPOSITORY")

    # Weekly downloads
    downloads = fetch_npm_downloads(name)
    result["weekly_downloads"] = downloads
    if downloads is not None and downloads < MIN_DOWNLOADS_CRITICAL:
        result["risks"].append(f"LOW_DOWNLOADS ({downloads:,})")

    return result


def is_critical_package(name: str) -> bool:
    """Check if package is in critical path."""
    name_lower = name.lower()
    return any(pattern in name_lower for pattern in CRITICAL_PATTERNS)


def extract_packages_from_lockfile(lockfile_path: Path) -> list[str]:
    """Extract unique package names from package-lock.json."""
    with open(lockfile_path) as f:
        data = json.load(f)

    packages = set()

    # v2/v3 lockfile format
    if "packages" in data:
        for key in data["packages"]:
            if key and not key.startswith("."):
                # Format: node_modules/package-name or node_modules/@scope/name
                parts = key.replace("node_modules/", "").split("/")
                if parts[0].startswith("@"):
                    packages.add("/".join(parts[:2]))
                else:
                    packages.add(parts[0])

    # v1 lockfile format
    if "dependencies" in data:

        def extract_deps(deps: dict):
            for name, info in deps.items():
                packages.add(name)
                if "dependencies" in info:
                    extract_deps(info["dependencies"])

        extract_deps(data["dependencies"])

    return sorted(packages)


def main():
    parser = argparse.ArgumentParser(description="Audit npm dependencies for supply-chain risks")
    parser.add_argument(
        "--lockfile",
        type=Path,
        default=Path("frontend/package-lock.json"),
        help="Path to package-lock.json",
    )
    parser.add_argument(
        "--all", action="store_true", help="Analyze all packages, not just critical-path"
    )
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    parser.add_argument(
        "--delay", type=float, default=0.2, help="Delay between API requests (seconds)"
    )
    args = parser.parse_args()

    if not args.lockfile.exists():
        print(f"Error: Lockfile not found: {args.lockfile}", file=sys.stderr)
        sys.exit(1)

    packages = extract_packages_from_lockfile(args.lockfile)
    print(f"Found {len(packages)} unique packages in lockfile", file=sys.stderr)

    # Filter to critical packages unless --all
    if not args.all:
        packages = [p for p in packages if is_critical_package(p)]
        print(f"Filtering to {len(packages)} critical-path packages", file=sys.stderr)

    results = []
    for i, pkg in enumerate(packages):
        print(f"[{i + 1}/{len(packages)}] Analyzing {pkg}...", file=sys.stderr)
        result = analyze_package(pkg)
        results.append(result)
        if args.delay > 0:
            time.sleep(args.delay)

    # Output
    if args.json:
        print(json.dumps(results, indent=2))
    else:
        # Text report
        flagged = [r for r in results if r["risks"]]
        print(f"\n{'=' * 60}")
        print("NPM DEPENDENCY AUDIT REPORT")
        print(f"{'=' * 60}")
        print(f"Total packages analyzed: {len(results)}")
        print(f"Packages with risk signals: {len(flagged)}")
        print()

        if flagged:
            print("FLAGGED PACKAGES:")
            print("-" * 40)
            for r in sorted(flagged, key=lambda x: len(x["risks"]), reverse=True):
                print(f"\n{r['name']}")
                print(
                    f"  Maintainers: {r['maintainer_count']} - {', '.join(r['maintainers'] or [])}"
                )
                print(
                    f"  Downloads/week: {r['weekly_downloads']:,}"
                    if r["weekly_downloads"]
                    else "  Downloads/week: N/A"
                )
                print(
                    f"  Last publish: {r['days_since_publish']} days ago"
                    if r["days_since_publish"]
                    else "  Last publish: N/A"
                )
                print(f"  Risks: {', '.join(r['risks'])}")
        else:
            print("No high-risk packages detected in critical path.")


if __name__ == "__main__":
    main()
