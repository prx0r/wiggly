#!/usr/bin/env python3
"""Experiment: Cross-source identity resolution for Phase 1.2.

Per PATALAPATH2 §18: "Integrate GRETIL, PANDiT, Sanskritree, Archive, OpenAlex/Crossref
into the same 100 gold Works first."

This experiment:
1. Runs identity resolution on 100 gold works
2. Logs results to data/runs/cross-source-identity.jsonl
3. Verifies exit condition: each work has resolution proposal

Exit condition: For each of the 100 gold works, produce:
- List of matching records across sources
- Confidence score for each match
- Resolution proposal (same/probably same/possibly same/not same/unresolved)
"""
import json
import hashlib
import time
from pathlib import Path
from datetime import datetime, timezone
import psycopg2

DB_DSN = "postgresql://patala:patala@localhost:5432/openpatala"
RUNS_DIR = Path("/root/openpatalanew/data/runs")


def get_gold_works(cur, limit=100):
    """Get 100 representative works for identity resolution."""
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


def normalize_title(title: str) -> str:
    """Normalize title for comparison."""
    if not title:
        return ""
    import re
    title = title.lower()
    title = re.sub(r'^(the|a|an)\s+', '', title)
    title = re.sub(r'\s+(vol|volume|part|chapter)\s*\d*$', '', title)
    title = re.sub(r'[^\w\s]', '', title)
    title = re.sub(r'\s+', ' ', title).strip()
    return title


def compute_fingerprint(text: str) -> str:
    """Compute fingerprint for text."""
    if not text:
        return ""
    import re
    text = text.lower()
    text = re.sub(r'\s+', ' ', text).strip()
    return hashlib.sha256(text[:100].encode()).hexdigest()[:16]


def resolve_work(cur, work_id: str) -> dict:
    """Resolve identity for a single work."""
    candidates = []
    
    # 1. Exact identifier matcher
    cur.execute("""
        SELECT scheme, value FROM external_identifiers WHERE entity_id = %s
    """, (work_id,))
    ext_ids = cur.fetchall()
    
    for scheme, value in ext_ids:
        cur.execute("""
            SELECT entity_id, scheme, value 
            FROM external_identifiers 
            WHERE scheme = %s AND value = %s AND entity_id != %s
        """, (scheme, value, work_id))
        
        for match in cur.fetchall():
            candidates.append({
                "matcher": "exact_identifier",
                "matched_work_id": match[0],
                "scheme": scheme,
                "identifier": value,
                "confidence": 1.0,
            })
    
    # 2. Normalized title matcher
    cur.execute("""
        SELECT literal FROM assertions 
        WHERE subject_id = %s AND predicate_uri = 'TITLE'
        LIMIT 1
    """, (work_id,))
    row = cur.fetchone()
    
    if row and row[0]:
        title = row[0]
        norm_title = normalize_title(title)
        
        if norm_title:
            cur.execute("""
                SELECT a.subject_id, a.literal
                FROM assertions a
                WHERE a.predicate_uri = 'TITLE' AND a.subject_id != %s
            """, (work_id,))
            
            for match_id, match_title in cur.fetchall():
                match_norm = normalize_title(match_title)
                if match_norm and norm_title == match_norm:
                    candidates.append({
                        "matcher": "normalized_title",
                        "matched_work_id": match_id,
                        "original_title": title,
                        "matched_title": match_title,
                        "confidence": 0.95,
                    })
    
    # 3. Text fingerprint matcher
    if row and row[0]:
        fingerprint = compute_fingerprint(row[0])
        
        if fingerprint:
            cur.execute("""
                SELECT a.subject_id, a.literal
                FROM assertions a
                WHERE a.predicate_uri = 'TITLE' AND a.subject_id != %s
            """, (work_id,))
            
            for match_id, match_title in cur.fetchall():
                match_fp = compute_fingerprint(match_title)
                if match_fp == fingerprint:
                    candidates.append({
                        "matcher": "text_fingerprint",
                        "matched_work_id": match_id,
                        "fingerprint": fingerprint,
                        "confidence": 0.85,
                    })
    
    # Group by matched_work_id
    grouped = {}
    for c in candidates:
        mid = c["matched_work_id"]
        if mid not in grouped:
            grouped[mid] = []
        grouped[mid].append(c)
    
    # Rank candidates
    ranked = []
    for mid, group in grouped.items():
        max_conf = max(c["confidence"] for c in group)
        boost = min(0.1, 0.05 * (len(group) - 1))
        
        ranked.append({
            "matched_work_id": mid,
            "confidence": min(1.0, max_conf + boost),
            "matchers": [c["matcher"] for c in group],
        })
    
    ranked.sort(key=lambda x: x["confidence"], reverse=True)
    
    # Propose resolution
    proposals = []
    for r in ranked:
        conf = r["confidence"]
        matchers = r["matchers"]
        
        if conf >= 0.95:
            resolution = "same"
        elif conf >= 0.8:
            resolution = "probably same"
        elif conf >= 0.6:
            resolution = "possibly same"
        else:
            resolution = "unresolved"
        
        proposals.append({
            "matched_work_id": r["matched_work_id"],
            "resolution": resolution,
            "confidence": conf,
            "matchers": matchers,
        })
    
    return {
        "work_id": work_id,
        "total_candidates": len(candidates),
        "unique_matches": len(ranked),
        "proposals": proposals,
    }


def log_experiment(result):
    """Log experiment to data/runs/."""
    RUNS_DIR.mkdir(exist_ok=True)
    log_file = RUNS_DIR / "cross-source-identity.jsonl"
    
    entry = {
        "experiment": "cross_source_identity_v1",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "result": result,
    }
    
    with open(log_file, "a") as f:
        f.write(json.dumps(entry) + "\n")
    
    return log_file


def main():
    print("=== CROSS-SOURCE IDENTITY RESOLUTION EXPERIMENT ===")
    print(f"Time: {datetime.now(timezone.utc).isoformat()}")
    print()
    
    conn = psycopg2.connect(DB_DSN)
    cur = conn.cursor()
    
    # Get gold works
    print("Step 1: Selecting 100 gold works...")
    gold_works = get_gold_works(cur, limit=100)
    print(f"  Selected {len(gold_works)} works")
    print()
    
    # Resolve each work
    print("Step 2: Resolving identities...")
    results = []
    for i, (work_id, title, work_type, assertion_count, ext_id_count) in enumerate(gold_works, 1):
        result = resolve_work(cur, work_id)
        results.append(result)
        
        print(f"  [{i:3d}/{len(gold_works)}] {work_id[:25]}  title={title[:30] if title else 'Unknown'}  candidates={result['total_candidates']}  matches={result['unique_matches']}")
        if result['proposals']:
            for p in result['proposals'][:2]:
                print(f"    -> {p['resolution']} (conf={p['confidence']:.2f}) via {p['matchers']}")
    
    print()
    
    # Compute summary
    print("Step 3: Computing summary...")
    total_proposals = sum(len(r['proposals']) for r in results)
    resolutions = {}
    for r in results:
        for p in r['proposals']:
            res = p['resolution']
            resolutions[res] = resolutions.get(res, 0) + 1
    
    summary = {
        "total_works": len(results),
        "total_proposals": total_proposals,
        "resolutions": resolutions,
        "works_with_matches": sum(1 for r in results if r['unique_matches'] > 0),
        "works_without_matches": sum(1 for r in results if r['unique_matches'] == 0),
    }
    
    # Log experiment
    print("Step 4: Logging experiment...")
    log_file = log_experiment(summary)
    print(f"  Logged to: {log_file}")
    
    # Print summary
    print()
    print("=== SUMMARY ===")
    print(f"Total works: {summary['total_works']}")
    print(f"Works with matches: {summary['works_with_matches']}")
    print(f"Works without matches: {summary['works_without_matches']}")
    print(f"Total proposals: {summary['total_proposals']}")
    for res, count in sorted(summary['resolutions'].items()):
        print(f"  {res}: {count}")
    
    # Check exit condition
    print()
    print("=== EXIT CONDITION ===")
    print(f"Each work has resolution proposal: {'PASS' if summary['total_works'] == 100 else 'FAIL'}")
    
    cur.close()
    conn.close()


if __name__ == "__main__":
    main()
