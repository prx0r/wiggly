#!/usr/bin/env python3
"""patala/identity.py — Cross-source identity resolution.

Per PATALAPATH2 §18: "Integrate GRETIL, PANDiT, Sanskritree, Archive, OpenAlex/Crossref
into the same 100 gold Works first."

Matchers:
1. ExactIdentifierMatcher — match by GRETIL/PANDiT/OpenAlex IDs
2. NormalizedTitleMatcher — match by normalized titles
3. AuthorTitleMatcher — match by author + title combination
4. TextFingerprintMatcher — match by text fingerprints
5. CandidateRanker — rank candidates by confidence
6. ResolutionProposal — propose same/probably same/possibly same/not same/unresolved

Output: same / probably same / possibly same / not same / unresolved
"""
import re
import hashlib
from typing import Optional
import psycopg2


DB_DSN = "postgresql://patala:patala@localhost:5432/openpatala"


class ExactIdentifierMatcher:
    """Match works by exact external identifiers."""
    
    def __init__(self, conn):
        self.conn = conn
    
    def find_matches(self, work_id: str) -> list[dict]:
        """Find works with matching external identifiers."""
        cur = self.conn.cursor()
        
        # Get all external identifiers for this work
        cur.execute("""
            SELECT scheme, value FROM external_identifiers WHERE entity_id = %s
        """, (work_id,))
        ext_ids = cur.fetchall()
        
        if not ext_ids:
            return []
        
        matches = []
        for scheme, value in ext_ids:
            # Find other works with the same identifier
            cur.execute("""
                SELECT entity_id, scheme, value 
                FROM external_identifiers 
                WHERE scheme = %s AND value = %s AND entity_id != %s
            """, (scheme, value, work_id))
            
            for match in cur.fetchall():
                matches.append({
                    "matcher": "exact_identifier",
                    "matched_work_id": match[0],
                    "scheme": scheme,
                    "identifier": value,
                    "confidence": 1.0,
                })
        
        cur.close()
        return matches


class NormalizedTitleMatcher:
    """Match works by normalized titles."""
    
    def __init__(self, conn):
        self.conn = conn
    
    def normalize_title(self, title: str) -> str:
        """Normalize title for comparison."""
        if not title:
            return ""
        
        # Lowercase
        title = title.lower()
        
        # Remove common prefixes/suffixes
        title = re.sub(r'^(the|a|an)\s+', '', title)
        title = re.sub(r'\s+(vol|volume|part|chapter)\s*\d*$', '', title)
        
        # Remove punctuation except spaces
        title = re.sub(r'[^\w\s]', '', title)
        
        # Collapse whitespace
        title = re.sub(r'\s+', ' ', title).strip()
        
        return title
    
    def find_matches(self, work_id: str, threshold: float = 0.8) -> list[dict]:
        """Find works with similar titles."""
        cur = self.conn.cursor()
        
        # Get title for this work
        cur.execute("""
            SELECT literal FROM assertions 
            WHERE subject_id = %s AND predicate_uri = 'TITLE'
            LIMIT 1
        """, (work_id,))
        row = cur.fetchone()
        if not row:
            return []
        
        title = row[0]
        norm_title = self.normalize_title(title)
        if not norm_title:
            return []
        
        # Get all titles from other works
        cur.execute("""
            SELECT a.subject_id, a.literal
            FROM assertions a
            WHERE a.predicate_uri = 'TITLE' AND a.subject_id != %s
        """, (work_id,))
        
        matches = []
        for match_id, match_title in cur.fetchall():
            match_norm = self.normalize_title(match_title)
            if not match_norm:
                continue
            
            # Simple similarity: check if normalized titles match exactly
            if norm_title == match_norm:
                matches.append({
                    "matcher": "normalized_title",
                    "matched_work_id": match_id,
                    "original_title": title,
                    "matched_title": match_title,
                    "confidence": 0.95,
                })
        
        cur.close()
        return matches


class AuthorTitleMatcher:
    """Match works by author + title combination."""
    
    def __init__(self, conn):
        self.conn = conn
    
    def find_matches(self, work_id: str) -> list[dict]:
        """Find works with matching author + title."""
        cur = self.conn.cursor()
        
        # Get author and title for this work
        cur.execute("""
            SELECT predicate_uri, literal FROM assertions 
            WHERE subject_id = %s AND predicate_uri IN ('AUTHOR', 'TITLE')
        """, (work_id,))
        
        assertions = cur.fetchall()
        authors = [a[1] for a in assertions if a[0] == 'AUTHOR']
        titles = [a[1] for a in assertions if a[0] == 'TITLE']
        
        if not authors or not titles:
            return []
        
        matches = []
        for author in authors:
            for title in titles:
                # Find works with same author and title
                cur.execute("""
                    SELECT DISTINCT a.subject_id
                    FROM assertions a
                    WHERE a.predicate_uri = 'AUTHOR' AND a.literal = %s
                    AND a.subject_id != %s
                    AND EXISTS (
                        SELECT 1 FROM assertions b
                        WHERE b.subject_id = a.subject_id
                        AND b.predicate_uri = 'TITLE' AND b.literal = %s
                    )
                """, (author, work_id, title))
                
                for match in cur.fetchall():
                    matches.append({
                        "matcher": "author_title",
                        "matched_work_id": match[0],
                        "author": author,
                        "title": title,
                        "confidence": 0.9,
                    })
        
        cur.close()
        return matches


class TextFingerprintMatcher:
    """Match works by text fingerprints."""
    
    def __init__(self, conn):
        self.conn = conn
    
    def compute_fingerprint(self, text: str) -> str:
        """Compute fingerprint for text."""
        if not text:
            return ""
        
        # Normalize text
        text = text.lower()
        text = re.sub(r'\s+', ' ', text).strip()
        
        # Take first 100 chars and hash
        return hashlib.sha256(text[:100].encode()).hexdigest()[:16]
    
    def find_matches(self, work_id: str) -> list[dict]:
        """Find works with matching text fingerprints."""
        cur = self.conn.cursor()
        
        # Get title for this work
        cur.execute("""
            SELECT literal FROM assertions 
            WHERE subject_id = %s AND predicate_uri = 'TITLE'
            LIMIT 1
        """, (work_id,))
        row = cur.fetchone()
        if not row:
            return []
        
        fingerprint = self.compute_fingerprint(row[0])
        if not fingerprint:
            return []
        
        # Find other works with same fingerprint
        cur.execute("""
            SELECT a.subject_id, a.literal
            FROM assertions a
            WHERE a.predicate_uri = 'TITLE' AND a.subject_id != %s
        """, (work_id,))
        
        matches = []
        for match_id, match_title in cur.fetchall():
            match_fp = self.compute_fingerprint(match_title)
            if match_fp == fingerprint:
                matches.append({
                    "matcher": "text_fingerprint",
                    "matched_work_id": match_id,
                    "fingerprint": fingerprint,
                    "confidence": 0.85,
                })
        
        cur.close()
        return matches


class CandidateRanker:
    """Rank candidates by confidence."""
    
    def rank_candidates(self, candidates: list[dict]) -> list[dict]:
        """Rank candidates by confidence score."""
        # Group by matched_work_id
        grouped = {}
        for c in candidates:
            mid = c["matched_work_id"]
            if mid not in grouped:
                grouped[mid] = []
            grouped[mid].append(c)
        
        # Compute aggregate confidence
        ranked = []
        for mid, group in grouped.items():
            # Use highest confidence from matchers
            max_conf = max(c["confidence"] for c in group)
            # Boost if multiple matchers agree
            boost = min(0.1, 0.05 * (len(group) - 1))
            
            ranked.append({
                "matched_work_id": mid,
                "confidence": min(1.0, max_conf + boost),
                "matchers": [c["matcher"] for c in group],
                "details": group,
            })
        
        # Sort by confidence descending
        ranked.sort(key=lambda x: x["confidence"], reverse=True)
        return ranked


class ResolutionProposal:
    """Propose resolution: same / probably same / possibly same / not same / unresolved."""
    
    def propose(self, ranked: list[dict]) -> list[dict]:
        """Propose resolution for each candidate."""
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
        
        return proposals


class IdentityResolver:
    """Main identity resolver combining all matchers."""
    
    def __init__(self, conn):
        self.conn = conn
        self.exact_matcher = ExactIdentifierMatcher(conn)
        self.title_matcher = NormalizedTitleMatcher(conn)
        self.author_title_matcher = AuthorTitleMatcher(conn)
        self.fingerprint_matcher = TextFingerprintMatcher(conn)
        self.ranker = CandidateRanker()
        self.proposer = ResolutionProposal()
    
    def resolve(self, work_id: str) -> dict:
        """Resolve identity for a work."""
        # Collect all candidates
        candidates = []
        candidates.extend(self.exact_matcher.find_matches(work_id))
        candidates.extend(self.title_matcher.find_matches(work_id))
        candidates.extend(self.author_title_matcher.find_matches(work_id))
        candidates.extend(self.fingerprint_matcher.find_matches(work_id))
        
        # Rank candidates
        ranked = self.ranker.rank_candidates(candidates)
        
        # Propose resolution
        proposals = self.proposer.propose(ranked)
        
        return {
            "work_id": work_id,
            "total_candidates": len(candidates),
            "unique_matches": len(ranked),
            "proposals": proposals,
        }


def main():
    """Test identity resolution on gold works."""
    conn = psycopg2.connect(DB_DSN)
    resolver = IdentityResolver(conn)
    
    # Get gold works
    cur = conn.cursor()
    cur.execute("""
        SELECT w.id, w.preferred_title
        FROM works w
        LEFT JOIN assertions a ON a.subject_id = w.id
        LEFT JOIN external_identifiers ei ON ei.entity_id = w.id
        GROUP BY w.id
        ORDER BY (COUNT(DISTINCT ei.id) * 2 + COUNT(DISTINCT a.id)) DESC
        LIMIT 10
    """)
    gold_works = cur.fetchall()
    
    print("=== IDENTITY RESOLUTION EXPERIMENT ===")
    print(f"Testing on {len(gold_works)} gold works")
    print()
    
    results = []
    for work_id, title in gold_works:
        result = resolver.resolve(work_id)
        results.append(result)
        
        print(f"Work: {work_id[:25]}  title={title[:40] if title else 'Unknown'}")
        print(f"  Candidates: {result['total_candidates']}, Matches: {result['unique_matches']}")
        if result['proposals']:
            for p in result['proposals'][:3]:
                print(f"  -> {p['resolution']} (conf={p['confidence']:.2f}) via {p['matchers']}")
        print()
    
    # Summary
    total_proposals = sum(len(r['proposals']) for r in results)
    resolutions = {}
    for r in results:
        for p in r['proposals']:
            res = p['resolution']
            resolutions[res] = resolutions.get(res, 0) + 1
    
    print("=== SUMMARY ===")
    print(f"Total proposals: {total_proposals}")
    for res, count in sorted(resolutions.items()):
        print(f"  {res}: {count}")
    
    conn.close()


if __name__ == "__main__":
    main()
