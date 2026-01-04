#!/usr/bin/env bash
# Version management script - bumps and syncs version across all files
# Usage: ./scripts/bump-version.sh [patch|minor|major|sync]

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"
VERSION_FILE="$ROOT_DIR/VERSION"

# Files to update (relative to root)
PYPROJECT="$ROOT_DIR/pyproject.toml"
PACKAGE_JSON="$ROOT_DIR/frontend/package.json"
VERSION_TS="$ROOT_DIR/frontend/src/lib/config/version.ts"
BO1_INIT="$ROOT_DIR/bo1/__init__.py"

get_version() {
    cat "$VERSION_FILE" | tr -d '[:space:]'
}

set_version() {
    local new_version="$1"
    echo "$new_version" > "$VERSION_FILE"
}

bump_version() {
    local current="$1"
    local part="$2"

    IFS='.' read -r major minor patch <<< "$current"

    case "$part" in
        major)
            echo "$((major + 1)).0.0"
            ;;
        minor)
            echo "${major}.$((minor + 1)).0"
            ;;
        patch)
            echo "${major}.${minor}.$((patch + 1))"
            ;;
        *)
            echo "Invalid bump type: $part" >&2
            exit 1
            ;;
    esac
}

sync_files() {
    local version="$1"

    # pyproject.toml
    if [[ -f "$PYPROJECT" ]]; then
        sed -i.bak -E "s/^version = \"[0-9]+\.[0-9]+\.[0-9]+\"/version = \"$version\"/" "$PYPROJECT"
        rm -f "$PYPROJECT.bak"
        echo "  Updated: pyproject.toml"
    fi

    # frontend/package.json
    if [[ -f "$PACKAGE_JSON" ]]; then
        sed -i.bak -E "s/\"version\": \"[0-9]+\.[0-9]+\.[0-9]+\"/\"version\": \"$version\"/" "$PACKAGE_JSON"
        rm -f "$PACKAGE_JSON.bak"
        echo "  Updated: frontend/package.json"
    fi

    # frontend/src/lib/config/version.ts
    if [[ -f "$VERSION_TS" ]]; then
        sed -i.bak -E "s/APP_VERSION = '[0-9]+\.[0-9]+\.[0-9]+'/APP_VERSION = '$version'/" "$VERSION_TS"
        rm -f "$VERSION_TS.bak"
        echo "  Updated: frontend/src/lib/config/version.ts"
    fi

    # bo1/__init__.py
    if [[ -f "$BO1_INIT" ]]; then
        sed -i.bak -E "s/__version__ = \"[0-9]+\.[0-9]+\.[0-9]+\"/__version__ = \"$version\"/" "$BO1_INIT"
        rm -f "$BO1_INIT.bak"
        echo "  Updated: bo1/__init__.py"
    fi
}

check_sync() {
    local version="$1"
    local errors=0

    # Check pyproject.toml
    if [[ -f "$PYPROJECT" ]]; then
        local py_ver=$(grep -E '^version = "' "$PYPROJECT" | sed -E 's/version = "([^"]+)"/\1/')
        if [[ "$py_ver" != "$version" ]]; then
            echo "  MISMATCH: pyproject.toml has $py_ver"
            errors=$((errors + 1))
        fi
    fi

    # Check package.json
    if [[ -f "$PACKAGE_JSON" ]]; then
        local pkg_ver=$(grep -E '"version":' "$PACKAGE_JSON" | head -1 | sed -E 's/.*"version": "([^"]+)".*/\1/')
        if [[ "$pkg_ver" != "$version" ]]; then
            echo "  MISMATCH: frontend/package.json has $pkg_ver"
            errors=$((errors + 1))
        fi
    fi

    # Check version.ts
    if [[ -f "$VERSION_TS" ]]; then
        local ts_ver=$(grep -E "APP_VERSION = '" "$VERSION_TS" | sed -E "s/.*APP_VERSION = '([^']+)'.*/\1/")
        if [[ "$ts_ver" != "$version" ]]; then
            echo "  MISMATCH: frontend/src/lib/config/version.ts has $ts_ver"
            errors=$((errors + 1))
        fi
    fi

    # Check bo1/__init__.py
    if [[ -f "$BO1_INIT" ]]; then
        local init_ver=$(grep -E '__version__ = "' "$BO1_INIT" | sed -E 's/__version__ = "([^"]+)"/\1/')
        if [[ "$init_ver" != "$version" ]]; then
            echo "  MISMATCH: bo1/__init__.py has $init_ver"
            errors=$((errors + 1))
        fi
    fi

    return $errors
}

main() {
    local action="${1:-}"

    if [[ -z "$action" ]]; then
        echo "Usage: $0 [patch|minor|major|sync|check]"
        echo ""
        echo "Commands:"
        echo "  patch  - Bump patch version (0.8.0 -> 0.8.1)"
        echo "  minor  - Bump minor version (0.8.0 -> 0.9.0)"
        echo "  major  - Bump major version (0.8.0 -> 1.0.0)"
        echo "  sync   - Sync VERSION to all files without bumping"
        echo "  check  - Verify all files match VERSION"
        exit 1
    fi

    local current_version=$(get_version)
    echo "Current version: $current_version"

    case "$action" in
        patch|minor|major)
            local new_version=$(bump_version "$current_version" "$action")
            echo "Bumping $action: $current_version -> $new_version"
            set_version "$new_version"
            sync_files "$new_version"
            echo ""
            echo "Version updated to $new_version"
            echo "Run 'git add -A && git commit -m \"chore: bump version to $new_version\"' to commit"
            ;;
        sync)
            echo "Syncing version $current_version to all files..."
            sync_files "$current_version"
            echo ""
            echo "All files synced to $current_version"
            ;;
        check)
            echo "Checking version sync..."
            if check_sync "$current_version"; then
                echo "All files in sync with VERSION ($current_version)"
                exit 0
            else
                echo ""
                echo "Version mismatch detected. Run '$0 sync' to fix."
                exit 1
            fi
            ;;
        *)
            echo "Unknown action: $action"
            exit 1
            ;;
    esac
}

main "$@"
