#!/usr/bin/env python3
"""Audit Python dependencies for supply-chain risk signals.

Checks critical-path packages for:
- Maintainer/author metadata
- Last release date (flag if > 2 years stale)
- Download stats via pypistats
"""

import argparse
import json
import subprocess
import sys
import time
from datetime import UTC, datetime
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import urlopen

# Critical-path package names to analyze
CRITICAL_PACKAGES = [
    "supertokens-python",
    "anthropic",
    "stripe",
    "pyjwt",
    "cryptography",
    "langchain",
    "langchain-core",
    "langgraph",
    "fastapi",
    "httpx",
    "aiohttp",
    "boto3",
    "redis",
    "sqlalchemy",
    "alembic",
    "resend",
]

# Risk thresholds
MAX_STALE_DAYS = 365  # 1 year for Python (more conservative)
MIN_MONTHLY_DOWNLOADS = 50_000


def fetch_pypi_info(package_name: str) -> dict[str, Any] | None:
    """Fetch package info from PyPI JSON API."""
    url = f"https://pypi.org/pypi/{package_name}/json"
    try:
        with urlopen(url, timeout=10) as resp:  # noqa: S310 - URL is hardcoded https
            return json.loads(resp.read().decode())
    except (URLError, HTTPError) as e:
        print(f"  Warning: Could not fetch {package_name}: {e}", file=sys.stderr)
        return None


def fetch_pypistats(package_name: str) -> int | None:
    """Fetch monthly download count from pypistats."""
    url = f"https://pypistats.org/api/packages/{package_name}/recent"
    try:
        with urlopen(url, timeout=10) as resp:  # noqa: S310 - URL is hardcoded https
            data = json.loads(resp.read().decode())
            return data.get("data", {}).get("last_month")
    except (URLError, HTTPError):
        return None


def analyze_package(name: str) -> dict[str, Any]:
    """Analyze a single PyPI package for risk signals."""
    result = {
        "name": name,
        "author": None,
        "author_email": None,
        "maintainer": None,
        "maintainer_email": None,
        "monthly_downloads": None,
        "last_release": None,
        "days_since_release": None,
        "home_page": None,
        "project_urls": None,
        "risks": [],
    }

    info = fetch_pypi_info(name)
    if not info:
        result["risks"].append("FETCH_FAILED")
        return result

    pkg_info = info.get("info", {})

    # Author/maintainer info
    result["author"] = pkg_info.get("author")
    result["author_email"] = pkg_info.get("author_email")
    result["maintainer"] = pkg_info.get("maintainer")
    result["maintainer_email"] = pkg_info.get("maintainer_email")
    result["home_page"] = pkg_info.get("home_page")
    result["project_urls"] = pkg_info.get("project_urls")

    # Check for missing maintainer info
    if not result["author"] and not result["maintainer"]:
        result["risks"].append("NO_MAINTAINER_INFO")

    # Last release date
    releases = info.get("releases", {})
    if releases:
        latest_date = None
        for _version, release_info in releases.items():
            if release_info:
                upload_time = release_info[0].get("upload_time_iso_8601")
                if upload_time:
                    try:
                        dt = datetime.fromisoformat(upload_time.replace("Z", "+00:00"))
                        if latest_date is None or dt > latest_date:
                            latest_date = dt
                    except ValueError:
                        pass

        if latest_date:
            result["last_release"] = latest_date.isoformat()
            days_old = (datetime.now(UTC) - latest_date).days
            result["days_since_release"] = days_old
            if days_old > MAX_STALE_DAYS:
                result["risks"].append(f"STALE ({days_old} days)")

    # Monthly downloads
    downloads = fetch_pypistats(name)
    result["monthly_downloads"] = downloads
    if downloads is not None and downloads < MIN_MONTHLY_DOWNLOADS:
        result["risks"].append(f"LOW_DOWNLOADS ({downloads:,})")

    return result


def get_installed_packages() -> list[str]:
    """Get list of installed packages from pip freeze."""
    try:
        output = subprocess.check_output(
            ["uv", "pip", "freeze"],  # noqa: S607 - intentional use of uv
            text=True,
            stderr=subprocess.DEVNULL,
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        try:
            output = subprocess.check_output(
                ["pip", "freeze"],  # noqa: S607 - intentional use of pip
                text=True,
                stderr=subprocess.DEVNULL,
            )
        except (subprocess.CalledProcessError, FileNotFoundError):
            return []

    packages = []
    for line in output.strip().split("\n"):
        if "==" in line:
            packages.append(line.split("==")[0].strip())
        elif line.startswith("-e"):
            continue  # Skip editable installs
    return packages


def main():
    parser = argparse.ArgumentParser(description="Audit Python dependencies for supply-chain risks")
    parser.add_argument("--all", action="store_true", help="Analyze all installed packages")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    parser.add_argument(
        "--delay", type=float, default=0.3, help="Delay between API requests (seconds)"
    )
    args = parser.parse_args()

    if args.all:
        packages = get_installed_packages()
        print(f"Found {len(packages)} installed packages", file=sys.stderr)
    else:
        packages = CRITICAL_PACKAGES
        print(f"Analyzing {len(packages)} critical-path packages", file=sys.stderr)

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
        print("PYTHON DEPENDENCY AUDIT REPORT")
        print(f"{'=' * 60}")
        print(f"Total packages analyzed: {len(results)}")
        print(f"Packages with risk signals: {len(flagged)}")
        print()

        if flagged:
            print("FLAGGED PACKAGES:")
            print("-" * 40)
            for r in sorted(flagged, key=lambda x: len(x["risks"]), reverse=True):
                print(f"\n{r['name']}")
                print(f"  Author: {r['author'] or 'N/A'}")
                print(f"  Maintainer: {r['maintainer'] or 'N/A'}")
                if r["monthly_downloads"]:
                    print(f"  Downloads/month: {r['monthly_downloads']:,}")
                else:
                    print("  Downloads/month: N/A")
                if r["days_since_release"]:
                    print(f"  Last release: {r['days_since_release']} days ago")
                else:
                    print("  Last release: N/A")
                print(f"  Risks: {', '.join(r['risks'])}")
        else:
            print("No high-risk packages detected in critical path.")

        # Summary of healthy packages
        healthy = [r for r in results if not r["risks"]]
        if healthy:
            print(f"\nHEALTHY PACKAGES ({len(healthy)}):")
            print("-" * 40)
            for r in healthy:
                dl = f"{r['monthly_downloads']:,}/mo" if r["monthly_downloads"] else "N/A"
                days = f"{r['days_since_release']}d" if r["days_since_release"] else "N/A"
                print(f"  {r['name']}: {dl}, last release {days}")


if __name__ == "__main__":
    main()
