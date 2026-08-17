#!/usr/bin/env python3
"""Experiment: Build gold work dossiers for Phase 1.1.

Per PATALAPATH2 §18: "Pick 100 representative Works.
Each must produce an excellent /works/{id}, /bundle, /coverage."

This experiment:
1. Queries the database for 100 representative works
2. Builds dossiers with assertions, ext_ids, events, coverage
3. Writes dossiers to data/gold/
4. Logs the experiment to data/runs/

Exit condition: 100 useful human-readable + agent-readable dossiers
"""
import json
import hashlib
import time
from pathlib import Path
from datetime import datetime, timezone
import psycopg2

DB_DSN = "postgresql://patala:patala@localhost:5432/openpatala"
GOLD_DIR = Path("/root/openpatalanew/data/gold")
RUNS_DIR = Path("/root/openpatalanew/data/runs")


def get_gold_works(cur, limit=100):
    """Get 100 representative works for dossiers.
    
    Selection criteria:
    - Works with most ext_ids (cross-source coverage)
    - Works with most assertions (data richness)
    - Works with diverse predicates (author, title, language, date)
    """
    cur.execute("""
        SELECT w.id, w.preferred_title, w.work_type,
               COUNT(DISTINCT a.id) as assertion_count,
               COUNT(DISTINCT ei.id) as ext_id_count
        FROM works w
        LEFT JOIN assertions a ON a.subject_id = w.id
        LEFT JOIN external_identifiers ei ON ei.entity_id = w.id
        GROUP BY w.id
        ORDER BY (COUNT(DISTINCT ei.id) * 2 + COUNT(DISTINCT a.id)) DESC
        LIMIT %s
    """, (limit,))
    return cur.fetchall()


def build_dossier(cur, work_id):
    """Build a single work dossier."""
    # Get work metadata
    cur.execute("SELECT preferred_title, work_type FROM works WHERE id = %s", (work_id,))
    title, work_type = cur.fetchone()

    # Get assertions
    cur.execute("""
        SELECT id, predicate_uri, object_id, literal, epistemic_mode, asserted_by, asserted_at
        FROM assertions WHERE subject_id = %s
    """, (work_id,))
    assertions = []
    for row in cur.fetchall():
        assertions.append({
            "id": row[0],
            "predicate": row[1],
            "object_id": row[2],
            "literal": row[3],
            "epistemic_mode": row[4],
            "asserted_by": row[5],
            "asserted_at": str(row[6]) if row[6] else None,
        })

    # Get external identifiers
    cur.execute("""
        SELECT id, scheme, value FROM external_identifiers WHERE entity_id = %s
    """, (work_id,))
    ext_ids = []
    for row in cur.fetchall():
        ext_ids.append({"id": row[0], "scheme": row[1], "identifier": row[2]})

    # Get events
    cur.execute("""
        SELECT event_id, event_type, occurred_at FROM events WHERE %s = ANY(entity_ids)
    """, (work_id,))
    events = []
    for row in cur.fetchall():
        events.append({
            "event_id": row[0],
            "event_type": row[1],
            "occurred_at": str(row[2]) if row[2] else None,
        })

    # Compute coverage
    predicates = {a["predicate"] for a in assertions}
    schemes = {e["scheme"] for e in ext_ids}

    coverage = {
        "has_author": "AUTHOR" in predicates,
        "has_title": "TITLE" in predicates,
        "has_language": "LANGUAGE" in predicates,
        "has_date": "DATE" in predicates,
        "has_tradition": "TRADITION" in predicates,
        "has_gretil": "GRETIL" in schemes,
        "has_openalex": "OPENALEX" in schemes,
        "has_crossref": "CROSSREF" in schemes,
        "has_archive": "ARCHIVE.ORG" in schemes,
        "has_pandit": "PANDIT" in schemes,
        "has_sanskritree": "SANSKRITREE" in schemes,
    }

    return {
        "work_id": work_id,
        "title": title or "Unknown",
        "work_type": work_type,
        "assertions": assertions,
        "assertions_count": len(assertions),
        "external_identifiers": ext_ids,
        "ext_ids_count": len(ext_ids),
        "events": events,
        "events_count": len(events),
        "coverage": coverage,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }


def log_experiment(result):
    """Log experiment to data/runs/."""
    RUNS_DIR.mkdir(exist_ok=True)
    log_file = RUNS_DIR / "gold-dossiers.jsonl"
    
    entry = {
        "experiment": "gold_dossiers_v1",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "result": result,
    }
    
    with open(log_file, "a") as f:
        f.write(json.dumps(entry) + "\n")
    
    return log_file


def main():
    print("=== GOLD WORK DOSSIERS EXPERIMENT ===")
    print(f"Time: {datetime.now(timezone.utc).isoformat()}")
    print()

    # Connect to database
    conn = psycopg2.connect(DB_DSN)
    cur = conn.cursor()

    # Get gold works
    print("Step 1: Selecting 100 representative works...")
    gold_works = get_gold_works(cur, limit=100)
    print(f"  Selected {len(gold_works)} works")

    # Build dossiers
    print("Step 2: Building dossiers...")
    GOLD_DIR.mkdir(exist_ok=True)
    
    dossiers = []
    for i, (work_id, title, work_type, assertion_count, ext_id_count) in enumerate(gold_works, 1):
        dossier = build_dossier(cur, work_id)
        dossiers.append(dossier)
        
        # Write to file
        filename = GOLD_DIR / f"{work_id[:25]}.json"
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(dossier, f, indent=2, ensure_ascii=False)
        
        print(f"  [{i:3d}/{len(gold_works)}] {work_id[:25]}  asserts={dossier['assertions_count']}  ext={dossier['ext_ids_count']}")

    # Compute summary
    print("Step 3: Computing summary...")
    total_assertions = sum(d["assertions_count"] for d in dossiers)
    total_ext_ids = sum(d["ext_ids_count"] for d in dossiers)
    total_events = sum(d["events_count"] for d in dossiers)
    
    works_with_author = sum(1 for d in dossiers if d["coverage"]["has_author"])
    works_with_gretil = sum(1 for d in dossiers if d["coverage"]["has_gretil"])
    works_with_translation = 0  # Need to check
    
    summary = {
        "total_works": len(dossiers),
        "total_assertions": total_assertions,
        "total_ext_ids": total_ext_ids,
        "total_events": total_events,
        "works_with_author": works_with_author,
        "works_with_gretil": works_with_gretil,
        "works_with_translation": works_with_translation,
    }

    # Log experiment
    print("Step 4: Logging experiment...")
    log_file = log_experiment(summary)
    print(f"  Logged to: {log_file}")

    # Print summary
    print()
    print("=== SUMMARY ===")
    print(f"Total works: {summary['total_works']}")
    print(f"Total assertions: {summary['total_assertions']}")
    print(f"Total ext_ids: {summary['total_ext_ids']}")
    print(f"Total events: {summary['total_events']}")
    print(f"Works with author: {summary['works_with_author']}")
    print(f"Works with GRETIL: {summary['works_with_gretil']}")
    print()
    print("=== EXIT CONDITION ===")
    print(f"100 dossiers written: {'PASS' if len(dossiers) == 100 else 'FAIL'}")

    # Clean up
    cur.close()
    conn.close()


if __name__ == "__main__":
    main()
