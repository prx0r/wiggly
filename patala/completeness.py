#!/usr/bin/env python3
"""patala/completeness.py — WorkCompleteness materialized projection.

Per newbuildmainspec §27-28:
- WorkCompleteness shows what Pāṭala knows and doesn't know about each work
- OpenPāṭala becomes a map of holes
- Projection is rebuildable from events + artifacts

"Tools don't become truth. Their outputs become observations." — newbuild
"""
from __future__ import annotations

import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from patala.hashing import uuid7


@dataclass
class WorkCompleteness:
    """Materialized projection of what Pāṭala knows about a work.

    Per newbuildmainspec §27: "OpenPāṭala becomes a map of holes."
    """
    work_id: str = ""
    identity: str = "UNRESOLVED"  # UNRESOLVED | CANDIDATE | RESOLVED | CONTESTED
    source: str = "NONE"  # NONE | CATALOG | SCAN | OCR | ETEXT | SCHOLARLY_ETEXT
    translation: str = "NONE_KNOWN"  # NONE_KNOWN | PARTIAL | EXISTING | PATALA_MACHINE | REVIEWED
    alignment: str = "NONE"  # NONE | PARTIAL | COMPLETE
    evaluation: str = "NONE"  # NONE | MACHINE | HUMAN | EXPERT
    bibliography: str = "NONE"  # NONE | PARTIAL | COMPLETE
    assertion_count: int = 0
    edition_count: int = 0
    translation_count: int = 0
    external_id_count: int = 0
    last_updated: str = ""


class CompletenessCompiler:
    """Compiles WorkCompleteness projections from stored data.

    Per newbuildmainspec §8: "Projection engine computes from events + artifacts."
    """

    def __init__(self):
        self._completeness: dict[str, WorkCompleteness] = {}

    def compile(self, work_id: str, work: dict, editions: list[dict],
                translations: list[dict], assertions: list[dict],
                external_ids: list[dict]) -> WorkCompleteness:
        """Compile completeness for a single work."""
        # Identity resolution
        identity = "UNRESOLVED"
        if work.get("preferred_title"):
            identity = "RESOLVED"
        if any(a.get("state") == "CONTESTED" for a in assertions):
            identity = "CONTESTED"

        # Source availability
        source = "NONE"
        if editions:
            has_etext = any(e.get("artifact_id") for e in editions)
            has_scholarly = any(e.get("quality_state") == "SCHOLARLY" for e in editions)
            if has_scholarly:
                source = "SCHOLARLY_ETEXT"
            elif has_etext:
                source = "ETEXT"
            else:
                source = "CATALOG"

        # Translation availability
        translation = "NONE_KNOWN"
        if translations:
            full = any(t.get("completeness") == "FULL" for t in translations)
            partial = any(t.get("completeness") == "PARTIAL" for t in translations)
            machine = any(t.get("provenance_refs") for t in translations)
            if full:
                translation = "EXISTING"
            elif partial:
                translation = "PARTIAL"
            elif machine:
                translation = "PATALA_MACHINE"
            else:
                translation = "EXISTING"

        # Bibliography
        bibliography = "NONE"
        if external_ids:
            has_doi = any(e.get("scheme") == "DOI" for e in external_ids)
            has_openalex = any(e.get("scheme") == "OPENALEX" for e in external_ids)
            if has_doi or has_openalex:
                bibliography = "COMPLETE"
            else:
                bibliography = "PARTIAL"

        completeness = WorkCompleteness(
            work_id=work_id,
            identity=identity,
            source=source,
            translation=translation,
            alignment="NONE",
            evaluation="NONE",
            bibliography=bibliography,
            assertion_count=len(assertions),
            edition_count=len(editions),
            translation_count=len(translations),
            external_id_count=len(external_ids),
        )

        self._completeness[work_id] = completeness
        return completeness

    def get(self, work_id: str) -> WorkCompleteness | None:
        """Get completeness for a work."""
        return self._completeness.get(work_id)

    def list_frontier(self, filter_type: str | None = None) -> list[dict]:
        """List works that need attention.

        Per newbuildmainspec §77: "The most important OpenPāṭala dashboard shows holes."
        """
        frontier = []
        for wid, comp in self._completeness.items():
            needs = []
            if comp.identity == "UNRESOLVED":
                needs.append("identity")
            if comp.source == "NONE":
                needs.append("source")
            if comp.translation == "NONE_KNOWN":
                needs.append("translation")
            if comp.bibliography == "NONE":
                needs.append("bibliography")

            if needs:
                frontier.append({
                    "work_id": wid,
                    "needs": needs,
                    "identity": comp.identity,
                    "source": comp.source,
                    "translation": comp.translation,
                    "bibliography": comp.bibliography,
                })

        if filter_type:
            frontier = [f for f in frontier if filter_type in f["needs"]]

        return frontier

    def stats(self) -> dict:
        """Overall completeness statistics."""
        total = len(self._completeness)
        if total == 0:
            return {"total": 0}

        resolved = sum(1 for c in self._completeness.values() if c.identity == "RESOLVED")
        with_source = sum(1 for c in self._completeness.values() if c.source != "NONE")
        with_translation = sum(1 for c in self._completeness.values() if c.translation != "NONE_KNOWN")

        return {
            "total": total,
            "resolved": resolved,
            "with_source": with_source,
            "with_translation": with_translation,
            "resolution_rate": round(resolved / total * 100, 1) if total else 0,
            "source_rate": round(with_source / total * 100, 1) if total else 0,
            "translation_rate": round(with_translation / total * 100, 1) if total else 0,
        }


if __name__ == "__main__":
    compiler = CompletenessCompiler()

    # Demo: compile completeness for some works
    works = [
        {"id": "PTW_001", "preferred_title": "Vigrahavyāvartanī"},
        {"id": "PTW_002", "preferred_title": "Mūlamadhyamakakārikā"},
        {"id": "PTW_003", "preferred_title": ""},  # unresolved
    ]

    editions = [
        {"id": "PTED_001", "work_id": "PTW_001", "artifact_id": "PTART_001"},
    ]

    translations = [
        {"id": "PTTR_001", "work_id": "PTW_001", "completeness": "FULL"},
    ]

    assertions = [
        {"id": "PTCAS_001", "subject_id": "PTW_001", "predicate": "AUTHOR", "state": "ACTIVE"},
    ]

    external_ids = [
        {"id": "PTEXT_001", "entity_id": "PTW_001", "scheme": "GRETIL", "value": "sa_gretil_001"},
    ]

    print("=== WorkCompleteness ===")
    for w in works:
        comp = compiler.compile(
            w["id"], w, editions if w["id"] == "PTW_001" else [],
            translations if w["id"] == "PTW_001" else [],
            assertions if w["id"] == "PTW_001" else [],
            external_ids if w["id"] == "PTW_001" else [],
        )
        print(f"  {w['id']}: identity={comp.identity} source={comp.source} "
              f"translation={comp.translation} assertions={comp.assertion_count}")

    print()
    print("=== Frontier (needs source) ===")
    frontier = compiler.list_frontier(filter_type="source")
    for f in frontier:
        print(f"  {f['work_id']}: needs {f['needs']}")

    print()
    print("=== Stats ===")
    stats = compiler.stats()
    print(f"  Total: {stats['total']}")
    print(f"  Resolved: {stats['resolved']} ({stats['resolution_rate']}%)")
    print(f"  With source: {stats['with_source']} ({stats['source_rate']}%)")
    print(f"  With translation: {stats['with_translation']} ({stats['translation_rate']}%)")
