#!/usr/bin/env python3
"""Experiment: Self-filling discovery system for Phase 1.6.

Per PATALAPATH2 §18: "Connect NRAH: Coverage → Gap → GapAction → NRAH → Discovery"

This experiment:
1. Identifies coverage gaps
2. Creates gap actions
3. Simulates NRAH discovery
4. Logs results to data/runs/self-filling-discovery.jsonl
5. Verifies exit condition: discoveries are made

Exit condition: At least 1 discovery is made
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
    log_file = RUNS_DIR / "self-filling-discovery.jsonl"
    
    entry = {
        "experiment": "self_filling_discovery_v1",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "result": result,
    }
    
    with open(log_file, "a") as f:
        f.write(json.dumps(entry) + "\n")
    
    return log_file


def main():
    print("=== SELF-FILLING DISCOVERY EXPERIMENT ===")
    print(f"Time: {datetime.now(timezone.utc).isoformat()}")
    print()
    
    # Import self-filling discovery
    import sys
    sys.path.insert(0, '/root/openpatalanew')
    from patala.discovery import SelfFillingDiscovery
    
    conn = psycopg2.connect(DB_DSN)
    discovery = SelfFillingDiscovery(conn)
    
    # Run discovery cycle
    print("Step 1: Running discovery cycle...")
    result = discovery.run_discovery_cycle()
    print()
    
    # Compute summary
    print("Step 2: Computing summary...")
    summary = {
        "gaps": result["gaps"],
        "actions": result["actions"],
        "discoveries": result["discoveries"],
        "discovery_rate": result["discoveries"] / result["actions"] if result["actions"] > 0 else 0,
    }
    
    # Log experiment
    print("Step 3: Logging experiment...")
    log_file = log_experiment(summary)
    print(f"  Logged to: {log_file}")
    
    # Print summary
    print()
    print("=== SUMMARY ===")
    print(f"Gaps: {summary['gaps']}")
    print(f"Actions: {summary['actions']}")
    print(f"Discoveries: {summary['discoveries']}")
    print(f"Discovery rate: {summary['discovery_rate']:.2%}")
    
    # Check exit condition
    print()
    print("=== EXIT CONDITION ===")
    print(f"At least 1 discovery: {'PASS' if summary['discoveries'] > 0 else 'FAIL'}")
    
    conn.close()


if __name__ == "__main__":
    main()
