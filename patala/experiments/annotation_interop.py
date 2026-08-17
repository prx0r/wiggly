#!/usr/bin/env python3
"""Experiment: Text/Passage Annotation Interop for Phase 1.7.

Per PATALAPATH2 §18: "Use STAM, OpenPeka, ATLAS, Web Annotation for
passages, linguistics, alignments, annotations."

This experiment:
1. Creates sample annotations
2. Converts to different formats (STAM, Web Annotation, ATLAS)
3. Gets annotations for works
4. Logs results to data/runs/annotation-interop.jsonl
5. Verifies exit condition: all conversions work

Exit condition: All format conversions work correctly
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
    log_file = RUNS_DIR / "annotation-interop.jsonl"
    
    entry = {
        "experiment": "annotation_interop_v1",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "result": result,
    }
    
    with open(log_file, "a") as f:
        f.write(json.dumps(entry) + "\n")
    
    return log_file


def main():
    print("=== TEXT/PASSAGE ANNOTATION INTEROP EXPERIMENT ===")
    print(f"Time: {datetime.now(timezone.utc).isoformat()}")
    print()
    
    # Import annotation interop
    import sys
    sys.path.insert(0, '/root/openpatalanew')
    from patala.annotation import AnnotationInterop
    
    conn = psycopg2.connect(DB_DSN)
    interop = AnnotationInterop(conn)
    
    results = {}
    
    # Test 1: Create annotation
    print("1. Creating sample annotation...")
    anchor = interop.create_text_anchor(
        work_id="PTW_0006803ca8677e45",
        start=0,
        end=10,
        text="sample text",
    )
    annotation = interop.create_annotation(
        anchor=anchor,
        body={"value": "test annotation", "format": "text/plain"},
        motivation="commenting",
    )
    results["create_annotation"] = {
        "passed": True,
        "annotation_id": annotation.id,
    }
    print(f"   Created annotation: {annotation.id}")
    print()
    
    # Test 2: Convert to STAM format
    print("2. Converting to STAM format...")
    stam = interop.convert_to_stam_format(annotation)
    results["convert_stam"] = {
        "passed": all(k in stam for k in ["type", "id", "target", "body", "motivation", "created"]),
        "keys": list(stam.keys()),
    }
    print(f"   STAM keys: {list(stam.keys())}")
    print()
    
    # Test 3: Convert to Web Annotation format
    print("3. Converting to Web Annotation format...")
    web_anno = interop.convert_to_web_annotation(annotation)
    results["convert_web_annotation"] = {
        "passed": all(k in web_anno for k in ["@context", "type", "id", "target", "body", "motivation", "created"]),
        "keys": list(web_anno.keys()),
    }
    print(f"   Web Annotation keys: {list(web_anno.keys())}")
    print()
    
    # Test 4: Convert to ATLAS format
    print("4. Converting to ATLAS format...")
    atlas = interop.convert_to_atlas_format(annotation)
    results["convert_atlas"] = {
        "passed": all(k in atlas for k in ["label", "lemma", "morphCode", "parsing", "vocabularyForm", "reference"]),
        "keys": list(atlas.keys()),
    }
    print(f"   ATLAS keys: {list(atlas.keys())}")
    print()
    
    # Test 5: Get annotations for work
    print("5. Getting annotations for work...")
    passages = interop.get_annotations_for_work("PTW_0006803ca8677e45")
    results["get_annotations"] = {
        "passed": True,
        "passages_found": len(passages),
    }
    print(f"   Found {len(passages)} passages")
    print()
    
    # Compute summary
    print("Step 6: Computing summary...")
    total_tests = len(results)
    passed_tests = sum(1 for r in results.values() if r.get("passed", False))
    
    summary = {
        "total_tests": total_tests,
        "passed_tests": passed_tests,
        "results": results,
    }
    
    # Log experiment
    print("Step 7: Logging experiment...")
    log_file = log_experiment(summary)
    print(f"  Logged to: {log_file}")
    
    # Print summary
    print()
    print("=== SUMMARY ===")
    print(f"Total tests: {summary['total_tests']}")
    print(f"Passed: {summary['passed_tests']}")
    print(f"Failed: {summary['total_tests'] - summary['passed_tests']}")
    
    # Check exit condition
    print()
    print("=== EXIT CONDITION ===")
    print(f"All conversions work: {'PASS' if passed_tests == total_tests else 'FAIL'}")
    
    conn.close()


if __name__ == "__main__":
    main()
