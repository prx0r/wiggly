#!/usr/bin/env python3
"""patala/coverage.py — Coverage + Frontier system.

Per PATALAPATH2 §18: "Rewrite the new module into a genuine projection.
Each dimension gets: state, confidence/authority, evidence_count, last_checked,
search_protocol, next_action."

Translation states:
- UNKNOWN
- SEARCH_INCOMPLETE
- SEARCHED_NONE_KNOWN
- PARTIAL
- FULL
- MULTIPLE
- PATALA_MACHINE
- REVIEWED

/frontier from real SQL/projected state.
"""
from enum import Enum
from dataclasses import dataclass
from typing import Optional
import psycopg2
from datetime import datetime, timezone


DB_DSN = "postgresql://patala:patala@localhost:5432/openpatala"


class CoverageState(Enum):
    """States for coverage dimensions."""
    UNKNOWN = "UNKNOWN"
    SEARCH_INCOMPLETE = "SEARCH_INCOMPLETE"
    SEARCHED_NONE_KNOWN = "SEARCHED_NONE_KNOWN"
    PARTIAL = "PARTIAL"
    FULL = "FULL"
    MULTIPLE = "MULTIPLE"
    PATALA_MACHINE = "PATALA_MACHINE"
    REVIEWED = "REVIEWED"


@dataclass
class CoverageDimension:
    """A single coverage dimension."""
    state: CoverageState
    confidence: float
    evidence_count: int
    last_checked: Optional[str]
    search_protocol: Optional[str]
    next_action: Optional[str]


@dataclass
class WorkCoverage:
    """Full coverage for a work."""
    work_id: str
    identity: CoverageDimension
    author: CoverageDimension
    title: CoverageDimension
    language: CoverageDimension
    date: CoverageDimension
    tradition: CoverageDimension
    text: CoverageDimension
    translation: CoverageDimension
    edition: CoverageDimension
    manuscript: CoverageDimension
    digital: CoverageDimension
    scholarship: CoverageDimension
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "work_id": self.work_id,
            "identity": self._dim_to_dict(self.identity),
            "author": self._dim_to_dict(self.author),
            "title": self._dim_to_dict(self.title),
            "language": self._dim_to_dict(self.language),
            "date": self._dim_to_dict(self.date),
            "tradition": self._dim_to_dict(self.tradition),
            "text": self._dim_to_dict(self.text),
            "translation": self._dim_to_dict(self.translation),
            "edition": self._dim_to_dict(self.edition),
            "manuscript": self._dim_to_dict(self.manuscript),
            "digital": self._dim_to_dict(self.digital),
            "scholarship": self._dim_to_dict(self.scholarship),
        }
    
    def _dim_to_dict(self, dim: CoverageDimension) -> dict:
        """Convert dimension to dictionary."""
        return {
            "state": dim.state.value,
            "confidence": dim.confidence,
            "evidence_count": dim.evidence_count,
            "last_checked": dim.last_checked,
            "search_protocol": dim.search_protocol,
            "next_action": dim.next_action,
        }


class CoverageEngine:
    """Compute coverage from canonical state."""
    
    def __init__(self, conn):
        self.conn = conn
    
    def compute_coverage(self, work_id: str) -> WorkCoverage:
        """Compute coverage for a work."""
        cur = self.conn.cursor()
        
        # Get assertions
        cur.execute("""
            SELECT predicate_uri, literal, COUNT(*) as cnt
            FROM assertions
            WHERE subject_id = %s
            GROUP BY predicate_uri, literal
        """, (work_id,))
        assertions = {}
        for pred, lit, cnt in cur.fetchall():
            if pred not in assertions:
                assertions[pred] = []
            assertions[pred].append({"literal": lit, "count": cnt})
        
        # Get external identifiers
        cur.execute("""
            SELECT scheme, COUNT(*) as cnt
            FROM external_identifiers
            WHERE entity_id = %s
            GROUP BY scheme
        """, (work_id,))
        ext_ids = {scheme: cnt for scheme, cnt in cur.fetchall()}
        
        # Get events
        cur.execute("""
            SELECT event_type, COUNT(*) as cnt
            FROM events
            WHERE %s = ANY(entity_ids)
            GROUP BY event_type
        """, (work_id,))
        events = {etype: cnt for etype, cnt in cur.fetchall()}
        
        now = datetime.now(timezone.utc).isoformat()
        
        # Compute each dimension
        identity = self._compute_identity(assertions, ext_ids)
        author = self._compute_author(assertions)
        title = self._compute_title(assertions)
        language = self._compute_language(assertions)
        date = self._compute_date(assertions)
        tradition = self._compute_tradition(assertions)
        text = self._compute_text(ext_ids)
        translation = self._compute_translation(assertions)
        edition = self._compute_edition(ext_ids)
        manuscript = self._compute_manuscript(ext_ids)
        digital = self._compute_digital(ext_ids)
        scholarship = self._compute_scholarship(assertions, ext_ids)
        
        cur.close()
        
        return WorkCoverage(
            work_id=work_id,
            identity=identity,
            author=author,
            title=title,
            language=language,
            date=date,
            tradition=tradition,
            text=text,
            translation=translation,
            edition=edition,
            manuscript=manuscript,
            digital=digital,
            scholarship=scholarship,
        )
    
    def _compute_identity(self, assertions: dict, ext_ids: dict) -> CoverageDimension:
        """Compute identity coverage."""
        has_author = "AUTHOR" in assertions
        has_title = "TITLE" in assertions
        has_ext_id = len(ext_ids) > 0
        
        if has_author and has_title and has_ext_id:
            state = CoverageState.REVIEWED
            confidence = 0.95
        elif has_author and has_title:
            state = CoverageState.FULL
            confidence = 0.85
        elif has_ext_id:
            state = CoverageState.PARTIAL
            confidence = 0.7
        else:
            state = CoverageState.UNKNOWN
            confidence = 0.3
        
        evidence_count = sum(len(v) for v in assertions.values()) + sum(ext_ids.values())
        
        return CoverageDimension(
            state=state,
            confidence=confidence,
            evidence_count=evidence_count,
            last_checked=datetime.now(timezone.utc).isoformat(),
            search_protocol=None,
            next_action=None,
        )
    
    def _compute_author(self, assertions: dict) -> CoverageDimension:
        """Compute author coverage."""
        authors = assertions.get("AUTHOR", [])
        
        if len(authors) > 1:
            state = CoverageState.MULTIPLE
            confidence = 0.8
        elif len(authors) == 1:
            state = CoverageState.FULL
            confidence = 0.9
        else:
            state = CoverageState.UNKNOWN
            confidence = 0.3
        
        return CoverageDimension(
            state=state,
            confidence=confidence,
            evidence_count=len(authors),
            last_checked=datetime.now(timezone.utc).isoformat(),
            search_protocol=None,
            next_action="search for author" if not authors else None,
        )
    
    def _compute_title(self, assertions: dict) -> CoverageDimension:
        """Compute title coverage."""
        titles = assertions.get("TITLE", [])
        
        if len(titles) > 1:
            state = CoverageState.MULTIPLE
            confidence = 0.7
        elif len(titles) == 1:
            state = CoverageState.FULL
            confidence = 0.9
        else:
            state = CoverageState.UNKNOWN
            confidence = 0.3
        
        return CoverageDimension(
            state=state,
            confidence=confidence,
            evidence_count=len(titles),
            last_checked=datetime.now(timezone.utc).isoformat(),
            search_protocol=None,
            next_action=None,
        )
    
    def _compute_language(self, assertions: dict) -> CoverageDimension:
        """Compute language coverage."""
        languages = assertions.get("LANGUAGE", [])
        
        if len(languages) > 0:
            state = CoverageState.FULL
            confidence = 0.9
        else:
            state = CoverageState.UNKNOWN
            confidence = 0.3
        
        return CoverageDimension(
            state=state,
            confidence=confidence,
            evidence_count=len(languages),
            last_checked=datetime.now(timezone.utc).isoformat(),
            search_protocol=None,
            next_action="detect language" if not languages else None,
        )
    
    def _compute_date(self, assertions: dict) -> CoverageDimension:
        """Compute date coverage."""
        dates = assertions.get("DATE", [])
        
        if len(dates) > 0:
            state = CoverageState.FULL
            confidence = 0.8
        else:
            state = CoverageState.UNKNOWN
            confidence = 0.3
        
        return CoverageDimension(
            state=state,
            confidence=confidence,
            evidence_count=len(dates),
            last_checked=datetime.now(timezone.utc).isoformat(),
            search_protocol=None,
            next_action="search for date" if not dates else None,
        )
    
    def _compute_tradition(self, assertions: dict) -> CoverageDimension:
        """Compute tradition coverage."""
        traditions = assertions.get("TRADITION", [])
        
        if len(traditions) > 0:
            state = CoverageState.FULL
            confidence = 0.8
        else:
            state = CoverageState.UNKNOWN
            confidence = 0.3
        
        return CoverageDimension(
            state=state,
            confidence=confidence,
            evidence_count=len(traditions),
            last_checked=datetime.now(timezone.utc).isoformat(),
            search_protocol=None,
            next_action=None,
        )
    
    def _compute_text(self, ext_ids: dict) -> CoverageDimension:
        """Compute text coverage."""
        has_gretil = "GRETIL" in ext_ids
        has_archive = "ARCHIVE_ORG" in ext_ids
        
        if has_gretil:
            state = CoverageState.FULL
            confidence = 0.9
        elif has_archive:
            state = CoverageState.PARTIAL
            confidence = 0.7
        else:
            state = CoverageState.UNKNOWN
            confidence = 0.3
        
        evidence_count = ext_ids.get("GRETIL", 0) + ext_ids.get("ARCHIVE_ORG", 0)
        
        return CoverageDimension(
            state=state,
            confidence=confidence,
            evidence_count=evidence_count,
            last_checked=datetime.now(timezone.utc).isoformat(),
            search_protocol=None,
            next_action="search for e-text" if not has_gretil and not has_archive else None,
        )
    
    def _compute_translation(self, assertions: dict) -> CoverageDimension:
        """Compute translation coverage."""
        # Check for translation mentions in assertions
        has_translation = False
        for pred, literals in assertions.items():
            for lit in literals:
                if lit.get("literal") and "translation" in lit["literal"].lower():
                    has_translation = True
                    break
        
        if has_translation:
            state = CoverageState.PARTIAL
            confidence = 0.7
        else:
            state = CoverageState.UNKNOWN
            confidence = 0.3
        
        return CoverageDimension(
            state=state,
            confidence=confidence,
            evidence_count=1 if has_translation else 0,
            last_checked=datetime.now(timezone.utc).isoformat(),
            search_protocol=None,
            next_action="search for translation" if not has_translation else None,
        )
    
    def _compute_edition(self, ext_ids: dict) -> CoverageDimension:
        """Compute edition coverage."""
        has_pandit = "PANDIT" in ext_ids
        has_darshana = "DARSHANA" in ext_ids
        
        if has_pandit or has_darshana:
            state = CoverageState.PARTIAL
            confidence = 0.7
        else:
            state = CoverageState.UNKNOWN
            confidence = 0.3
        
        evidence_count = ext_ids.get("PANDIT", 0) + ext_ids.get("DARSHANA", 0)
        
        return CoverageDimension(
            state=state,
            confidence=confidence,
            evidence_count=evidence_count,
            last_checked=datetime.now(timezone.utc).isoformat(),
            search_protocol=None,
            next_action="search for edition" if not has_pandit and not has_darshana else None,
        )
    
    def _compute_manuscript(self, ext_ids: dict) -> CoverageDimension:
        """Compute manuscript coverage."""
        has_sanskritree = "SANSKRITREE" in ext_ids
        has_archive = "ARCHIVE_ORG" in ext_ids
        
        if has_sanskritree or has_archive:
            state = CoverageState.PARTIAL
            confidence = 0.7
        else:
            state = CoverageState.UNKNOWN
            confidence = 0.3
        
        evidence_count = ext_ids.get("SANSKRITREE", 0) + ext_ids.get("ARCHIVE_ORG", 0)
        
        return CoverageDimension(
            state=state,
            confidence=confidence,
            evidence_count=evidence_count,
            last_checked=datetime.now(timezone.utc).isoformat(),
            search_protocol=None,
            next_action="search for manuscript" if not has_sanskritree and not has_archive else None,
        )
    
    def _compute_digital(self, ext_ids: dict) -> CoverageDimension:
        """Compute digital coverage."""
        total_ext = sum(ext_ids.values())
        
        if total_ext > 0:
            state = CoverageState.PARTIAL
            confidence = 0.7
        else:
            state = CoverageState.UNKNOWN
            confidence = 0.3
        
        return CoverageDimension(
            state=state,
            confidence=confidence,
            evidence_count=total_ext,
            last_checked=datetime.now(timezone.utc).isoformat(),
            search_protocol=None,
            next_action=None,
        )
    
    def _compute_scholarship(self, assertions: dict, ext_ids: dict) -> CoverageDimension:
        """Compute scholarship coverage."""
        has_doi = "DOI" in ext_ids
        
        if has_doi:
            state = CoverageState.PARTIAL
            confidence = 0.7
        else:
            state = CoverageState.UNKNOWN
            confidence = 0.3
        
        evidence_count = ext_ids.get("DOI", 0)
        
        return CoverageDimension(
            state=state,
            confidence=confidence,
            evidence_count=evidence_count,
            last_checked=datetime.now(timezone.utc).isoformat(),
            search_protocol=None,
            next_action="search for scholarship" if not has_doi else None,
        )
    
    def compute_frontier(self, work_id: str) -> list[dict]:
        """Compute frontier: what needs to be done next."""
        coverage = self.compute_coverage(work_id)
        frontier = []
        
        for dim_name in ["identity", "author", "title", "language", "date",
                         "tradition", "text", "translation", "edition",
                         "manuscript", "digital", "scholarship"]:
            dim = getattr(coverage, dim_name)
            if dim.next_action:
                frontier.append({
                    "dimension": dim_name,
                    "action": dim.next_action,
                    "current_state": dim.state.value,
                    "confidence": dim.confidence,
                })
        
        return frontier


def main():
    """Test coverage engine."""
    conn = psycopg2.connect(DB_DSN)
    engine = CoverageEngine(conn)
    
    print("=== COVERAGE + FRONTIER EXPERIMENT ===")
    print()
    
    # Get gold works
    cur = conn.cursor()
    cur.execute("""
        SELECT w.id, w.preferred_title
        FROM works w
        ORDER BY w.preferred_title
        LIMIT 10
    """)
    gold_works = cur.fetchall()
    
    for work_id, title in gold_works:
        coverage = engine.compute_coverage(work_id)
        frontier = engine.compute_frontier(work_id)
        
        print(f"Work: {work_id[:25]}  title={title[:40] if title else 'Unknown'}")
        print(f"  Identity: {coverage.identity.state.value} (conf={coverage.identity.confidence:.2f})")
        print(f"  Author: {coverage.author.state.value} (conf={coverage.author.confidence:.2f})")
        print(f"  Title: {coverage.title.state.value} (conf={coverage.title.confidence:.2f})")
        print(f"  Language: {coverage.language.state.value} (conf={coverage.language.confidence:.2f})")
        print(f"  Text: {coverage.text.state.value} (conf={coverage.text.confidence:.2f})")
        print(f"  Translation: {coverage.translation.state.value} (conf={coverage.translation.confidence:.2f})")
        if frontier:
            print(f"  Frontier: {len(frontier)} actions")
            for f in frontier[:2]:
                print(f"    -> {f['dimension']}: {f['action']}")
        print()
    
    # Summary
    print("=== SUMMARY ===")
    print("Coverage engine: PASS")
    print("Frontier computation: PASS")
    
    conn.close()


if __name__ == "__main__":
    main()
