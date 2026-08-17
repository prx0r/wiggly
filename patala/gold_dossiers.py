#!/usr/bin/env python3
"""patala/gold_dossiers.py — Build gold work dossiers.

Per PATALAPATH2 §18: "Pick 100 representative Works.
Each must produce an excellent /works/{id}, /bundle, /coverage."

This script generates dossiers for gold works.
"""
import json
import psycopg2
from pathlib import Path
from datetime import datetime


DB_DSN = "postgresql://patala:patala@localhost:5432/openpatala"


def get_gold_works(cur, limit=100):
    """Get the most interesting works for dossiers."""
    cur.execute("""
        SELECT w.id, w.preferred_title, w.work_type,
               COUNT(DISTINCT a.id) as assertion_count,
               COUNT(DISTINCT ei.id) as ext_id_count
        FROM works w
        LEFT JOIN assertions a ON a.subject_id = w.id
        LEFT JOIN external_identifiers ei ON ei.entity_id = w.id
        GROUP BY w.id
        ORDER BY (COUNT(DISTINCT a.id) + COUNT(DISTINCT ei.id)) DESC
        LIMIT %s
    """, (limit,))
    return cur.fetchall()


def build_work_dossier(cur, work_id, title, work_type, assertion_count, ext_id_count):
    """Build a single work dossier."""
    # Get assertions
    cur.execute("""
        SELECT id, predicate_uri, object_id, literal, epistemic_mode,
               asserted_by, asserted_at
        FROM assertions
        WHERE subject_id = %s
    """, (work_id,))
    assertions = cur.fetchall()

    # Get external identifiers
    cur.execute("""
        SELECT id, scheme, value
        FROM external_identifiers
        WHERE entity_id = %s
    """, (work_id,))
    ext_ids = cur.fetchall()

    # Get events
    cur.execute("""
        SELECT event_id, event_type, occurred_at
        FROM events
        WHERE %s = ANY(entity_ids)
    """, (work_id,))
    events = cur.fetchall()

    # Build assertions list
    assertions_list = []
    for a in assertions:
        assertions_list.append({
            "id": a[0],
            "predicate": a[1],
            "object_id": a[2],
            "literal": a[3],
            "epistemic_mode": a[4],
            "asserted_by": a[5],
            "asserted_at": str(a[6]) if a[6] else None,
        })

    # Build ext_ids list
    ext_ids_list = []
    for e in ext_ids:
        ext_ids_list.append({
            "id": e[0],
            "scheme": e[1],
            "identifier": e[2],
        })

    # Build events list
    events_list = []
    for ev in events:
        events_list.append({
            "id": ev[0],
            "event_type": ev[1],
            "occurred_at": str(ev[2]) if ev[2] else None,
        })

    # Build coverage
    coverage = compute_coverage(assertions_list, ext_ids_list, events_list)

    return {
        "work_id": work_id,
        "title": title or "Unknown",
        "work_type": work_type,
        "assertions_count": len(assertions_list),
        "ext_ids_count": len(ext_ids_list),
        "events_count": len(events_list),
        "assertions": assertions_list,
        "external_identifiers": ext_ids_list,
        "events": events_list,
        "coverage": coverage,
        "created_at": datetime.utcnow().isoformat() + "Z",
    }


def compute_coverage(assertions, ext_ids, events):
    """Compute coverage from canonical state."""
    predicates = set(a.get("predicate", "") for a in assertions)
    schemes = set(e.get("scheme", "") for e in ext_ids)

    return {
        "has_author": "author" in predicates,
        "has_title": "title" in predicates,
        "has_genre": "genre" in predicates,
        "has_gretil": any("gretil" in s.lower() for s in schemes),
        "has_openalex": any("openalex" in s.lower() for s in schemes),
        "has_crossref": any("crossref" in s.lower() for s in schemes),
        "has_archive": any("archive.org" in s.lower() for s in schemes),
        "has_translation": any("translation" in a.get("literal", "").lower() for a in assertions),
        "has_edition": any("edition" in a.get("literal", "").lower() for a in assertions),
    }


def main():
    conn = psycopg2.connect(DB_DSN)
    cur = conn.cursor()

    gold_works = get_gold_works(cur, limit=100)
    print(f"Building dossiers for {len(gold_works)} gold works...")

    output_dir = Path("/root/openpatalanew/data/gold")
    output_dir.mkdir(exist_ok=True)

    for i, (work_id, title, work_type, assertion_count, ext_id_count) in enumerate(gold_works, 1):
        dossier = build_work_dossier(cur, work_id, title, work_type, assertion_count, ext_id_count)
        filename = output_dir / f"{work_id[:25]}.json"
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(dossier, f, indent=2, ensure_ascii=False)
        print(f"  [{i:3d}/{len(gold_works)}] {work_id[:25]}  assertions={dossier['assertions_count']}  ext_ids={dossier['ext_ids_count']}")

    print(f"\nDone. {len(gold_works)} dossiers written to {output_dir}")

    cur.close()
    conn.close()


if __name__ == "__main__":
    main()
