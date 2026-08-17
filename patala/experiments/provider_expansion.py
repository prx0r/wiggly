#!/usr/bin/env python3
"""Experiment: Provider expansion system for Phase 1.5.

Per PATALAPATH2 §18: "Steal Garglecum + MMM mechanisms.
Every provider gets: adapter, mapping, fixtures, health, canary,
freshness, yield, rights policy, crosswalk rate."

This experiment:
1. Computes provider health
2. Computes provider coverage
3. Computes median providers per work
4. Identifies coverage gaps
5. Logs results to data/runs/provider-expansion.jsonl
6. Verifies exit condition: all providers have health computed

Exit condition: All providers have health computed
"""
import json
import time
from pathlib import Path
from datetime import datetime, timezone
import psycopg2

DB_DSN = "postgresql://patala:patala@localhost:5432/openpatala"
RUNS_DIR = Path("/root/openpatalanew/data/runs")


def log_experiment(result):
    """Log experiment to data/runs/."""
    RUNS_DIR.mkdir(exist_ok=True)
    log_file = RUNS_DIR / "provider-expansion.jsonl"
    
    entry = {
        "experiment": "provider_expansion_v1",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "result": result,
    }
    
    with open(log_file, "a") as f:
        f.write(json.dumps(entry) + "\n")
    
    return log_file


def main():
    print("=== PROVIDER EXPANSION EXPERIMENT ===")
    print(f"Time: {datetime.now(timezone.utc).isoformat()}")
    print()
    
    # Import provider expansion
    import sys
    sys.path.insert(0, '/root/openpatalanew')
    from patala.providers import ProviderExpansion
    
    conn = psycopg2.connect(DB_DSN)
    expansion = ProviderExpansion(conn)
    
    # Get provider health
    print("Step 1: Computing provider health...")
    health = expansion.get_provider_health()
    print(f"  Found {len(health)} providers")
    print()
    
    # Get provider coverage
    print("Step 2: Computing provider coverage...")
    coverage = expansion.get_provider_coverage()
    print(f"  Found {len(coverage)} providers")
    print()
    
    # Get median providers per work
    print("Step 3: Computing median providers per work...")
    median = expansion.get_median_providers_per_work()
    print(f"  Median: {median:.2f}")
    print()
    
    # Get coverage gaps
    print("Step 4: Identifying coverage gaps...")
    gaps = expansion.get_coverage_gaps()
    print(f"  Found {len(gaps)} gaps")
    print()
    
    # Compute summary
    print("Step 5: Computing summary...")
    healthy_providers = sum(1 for h in health if h.is_healthy)
    total_providers = len(health)
    total_coverage = sum(c.works_covered for c in coverage)
    total_works = coverage[0].total_works if coverage else 0
    
    summary = {
        "total_providers": total_providers,
        "healthy_providers": healthy_providers,
        "median_providers_per_work": median,
        "total_coverage": total_coverage,
        "total_works": total_works,
        "coverage_gaps": len(gaps),
    }
    
    # Log experiment
    print("Step 6: Logging experiment...")
    log_file = log_experiment(summary)
    print(f"  Logged to: {log_file}")
    
    # Print summary
    print()
    print("=== SUMMARY ===")
    print(f"Total providers: {summary['total_providers']}")
    print(f"Healty providers: {summary['healthy_providers']}")
    print(f"Median providers per work: {summary['median_providers_per_work']:.2f}")
    print(f"Total coverage: {summary['total_coverage']}/{summary['total_works']}")
    print(f"Coverage gaps: {summary['coverage_gaps']}")
    
    # Check exit condition
    print()
    print("=== EXIT CONDITION ===")
    print(f"All providers have health: {'PASS' if healthy_providers == total_providers else 'FAIL'}")
    
    conn.close()


if __name__ == "__main__":
    main()
