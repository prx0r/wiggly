#!/usr/bin/env python3
"""patala/adapters/validate.py — Validate that adapters are real.

Per newbuild: "No placeholders. Production build."

Checks each adapter:
1. Does it call an external API? (real adapter)
2. Does it read from local files? (local parser)
3. Is it just scaffolded? (placeholder)

Returns a report of what's real vs fake.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ADAPTERS_DIR = Path(__file__).resolve().parent


def validate_adapter(adapter_name: str) -> dict:
    """Validate a single adapter."""
    adapter_dir = ADAPTERS_DIR / adapter_name
    if not adapter_dir.exists():
        return {"name": adapter_name, "status": "MISSING", "type": "none"}

    adapter_file = adapter_dir / "adapter.py"
    if not adapter_file.exists():
        return {"name": adapter_name, "status": "MISSING", "type": "no_code"}

    code = adapter_file.read_text(encoding="utf-8")

    # Count API URLs vs local file operations
    api_urls = re.findall(r'https?://[^\s"\'<>]+', code)
    local_ops = re.findall(r'Path\(|\.read_text|\.json|\.xml|\.ts|zipfile|corpus/', code)
    has_scaffold = bool(re.search(r'return \{\}|raise NotImplementedError', code))

    # Determine type based on ratio
    api_count = len(api_urls)
    local_count = len(local_ops)

    if has_scaffold and api_count == 0 and local_count == 0:
        adapter_type = "placeholder"
        status = "SCAFFOLDED"
    elif api_count > 0 and local_count == 0:
        adapter_type = "api"
        status = "REAL"
    elif local_count > 0 and api_count == 0:
        adapter_type = "local"
        status = "LOCAL_FILE"
    elif api_count > local_count:
        # More API calls than local ops = primarily API
        adapter_type = "api"
        status = "REAL"
    elif local_count > api_count:
        # More local ops than API = primarily local
        adapter_type = "local"
        status = "LOCAL_FILE"
    else:
        adapter_type = "mixed"
        status = "MIXED"

    return {
        "name": adapter_name,
        "status": status,
        "type": adapter_type,
        "api_urls": api_urls[:3],  # Show first 3
        "local_ops": local_count,
    }

    return {
        "name": adapter_name,
        "status": status,
        "type": adapter_type,
        "has_api": has_api,
        "has_local": has_local,
        "has_scaffold": has_scaffold,
    }


def validate_all_adapters() -> list[dict]:
    """Validate all adapters."""
    results = []
    for adapter_dir in sorted(ADAPTERS_DIR.iterdir()):
        if adapter_dir.is_dir() and not adapter_dir.name.startswith("_"):
            results.append(validate_adapter(adapter_dir.name))
    return results


def print_report(results: list[dict]):
    """Print validation report."""
    print("=== ADAPTER VALIDATION REPORT ===")
    print()

    real = [r for r in results if r["status"] == "REAL"]
    local = [r for r in results if r["status"] == "LOCAL_FILE"]
    scaffolded = [r for r in results if r["status"] == "SCAFFOLDED"]

    print(f"REAL API adapters: {len(real)}")
    for r in real:
        print(f"  ✅ {r['name']} ({r['type']})")

    print(f"\nLOCAL FILE parsers: {len(local)}")
    for r in local:
        print(f"  ⚠️  {r['name']} ({r['type']})")

    print(f"\nSCAFFOLDED only: {len(scaffolded)}")
    for r in scaffolded:
        print(f"  ❌ {r['name']} ({r['type']})")

    print(f"\nTotal: {len(results)} adapters")
    print(f"  Real: {len(real)}")
    print(f"  Local: {len(local)}")
    print(f"  Scaffolded: {len(scaffolded)}")


if __name__ == "__main__":
    results = validate_all_adapters()
    print_report(results)
