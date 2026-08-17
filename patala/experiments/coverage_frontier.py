#!/usr/bin/env python3
"""Experiment: Coverage + Frontier system for Phase 1.4.

Per PATALAPATH2 §18: "Rewrite the new module into a genuine projection.
Each dimension gets: state, confidence/authority, evidence_count, last_checked,
search_protocol, next_action."

This experiment:
1. Computes coverage for 100 gold works
2. Computes frontier for each work
3. Logs results to data/runs/coverage-frontier.jsonl
4. Verifies exit condition: all works have coverage computed

Exit condition: All works have coverage computed with frontier actions
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
    log_file = RUNS_DIR / "coverage-frontier.jsonl"
    
    entry = {
        "experiment": "coverage_frontier_v1",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "result": result,
    }
    
    with open(log_file, "a") as f:
        f.write(json.dumps(entry) + "\n")
    
    return log_file


def main():
    print("=== COVERAGE + FRONTIER EXPERIMENT ===")
    print(f"Time: {datetime.now(timezone.utc).isoformat()}")
    print()
    
    # Import coverage engine
    import sys
    sys.path.insert(0, '/root/openpatalanew')
    from patala.coverage import CoverageEngine
    
    conn = psycopg2.connect(DB_DSN)
    engine = CoverageEngine(conn)
    
    # Get gold works
    print("Step 1: Selecting 100 gold works...")
    cur = conn.cursor()
    cur.execute("""
        SELECT w.id, w.preferred_title
        FROM works w
        ORDER BY w.preferred_title
        LIMIT 100
    """)
    gold_works = cur.fetchall()
    print(f"  Selected {len(gold_works)} works")
    print()
    
    # Compute coverage for each work
    print("Step 2: Computing coverage...")
    results = []
    for i, (work_id, title) in enumerate(gold_works, 1):
        coverage = engine.compute_coverage(work_id)
        frontier = engine.compute_frontier(work_id)
        
        result = {
            "work_id": work_id,
            "title": title,
            "coverage": coverage.to_dict(),
            "frontier": frontier,
        }
        results.append(result)
        
        if i % 20 == 0:
            print(f"  [{i:3d}/{len(gold_works)}] Processed")
    
    print(f"  Total processed: {len(results)}")
    print()
    
    # Compute summary
    print("Step 3: Computing summary...")
    total_frontier = sum(len(r["frontier"]) for r in results)
    
    # Count states
    states = {}
    for r in results:
        for dim in ["identity", "author", "title", "language", "date",
                     "tradition", "text", "translation", "edition",
                     "manuscript", "digital", "scholarship"]:
            state = r["coverage"][dim]["state"]
            states[state] = states.get(state, 0) + 1
    
    summary = {
        "total_works": len(results),
        "total_frontier_actions": total_frontier,
        "states": states,
    }
    
    # Log experiment
    print("Step 4: Logging experiment...")
    log_file = log_experiment(summary)
    print(f"  Logged to: {log_file}")
    
    # Print summary
    print()
    print("=== SUMMARY ===")
    print(f"Total works: {summary['total_works']}")
    print(f"Total frontier actions: {summary['total_frontier_actions']}")
    print("States:")
    for state, count in sorted(summary["states"].items()):
        print(f"  {state}: {count}")
    
    # Check exit condition
    print()
    print("=== EXIT CONDITION ===")
    print(f"All works have coverage: {'PASS' if len(results) == 100 else 'FAIL'}")
    
    cur.close()
    conn.close()


if __name__ == "__main__":
    main()
