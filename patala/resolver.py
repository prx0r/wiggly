#!/usr/bin/env python3
"""patala/resolver.py — staged identity resolver (R0-R3).

Per newbuildmainspec §45-47:
- R0: exact external ID match
- R1: exact deterministic crosswalk
- R2: exact normalized bibliographic composite (title + author + edition/year)
- R3: high-confidence candidate (fuzzy/embedding/LLM — never auto-merge)

"Tools don't become truth. Their outputs become observations." — newbuild
"""
from __future__ import annotations

import hashlib
import sys
from dataclasses import dataclass, field
from typing import Any

sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parents[1]))
from patala.hashing import uuid7, semantic_fingerprint


@dataclass
class ResolutionProposal:
    """A proposal to resolve candidate(s) to an entity.

    Per newbuildmainspec §46: "Keep thresholds conservative.
    False merges are more damaging than duplicate entities."
    """
    id: str = field(default_factory=lambda: f"PTRSL_{uuid7()}")
    candidate_ids: list[str] = field(default_factory=list)
    proposed_entity_id: str | None = None
    relation: str = "PROBABLE_IDENTITY"
    feature_evidence: dict = field(default_factory=dict)
    method: str = ""
    confidence: float = 0.0
    auto_action: str = "REVIEW"  # MERGE | LINK_PROBABLE | REVIEW | REJECT
    created_at: str = ""


class Resolver:
    """Staged identity resolver.

    Per newbuildmainspec §45:
    R0: exact external ID → direct match
    R1: exact deterministic crosswalk (same ID scheme mapping)
    R2: normalized bibliographic composite (title + author + year)
    R3: high-confidence candidate (fuzzy — never auto-merge)
    """

    def __init__(self):
        self._external_index: dict[str, str] = {}  # scheme:value → entity_id
        self._fingerprint_index: dict[str, str] = {}  # fingerprint → entity_id
        self._entities: dict[str, dict] = {}  # entity_id → entity record

    def register_entity(self, entity_id: str, record: dict):
        """Register an entity for resolution."""
        self._entities[entity_id] = record

    def register_external_id(self, scheme: str, value: str, entity_id: str):
        """Register an external ID mapping."""
        key = f"{scheme}:{value}"
        self._external_index[key] = entity_id

    def register_fingerprint(self, fingerprint: str, entity_id: str):
        """Register a normalized fingerprint."""
        self._fingerprint_index[fingerprint] = entity_id

    def resolve(self, candidates: list[dict]) -> ResolutionProposal:
        """Resolve a list of candidates to an entity using staged matching.

        Per newbuildmainspec §45:
        - Try R0 first (exact external ID)
        - Then R1 (deterministic crosswalk)
        - Then R2 (bibliographic composite)
        - R3 is high-confidence but never auto-merge
        """
        if not candidates:
            return ResolutionProposal(
                auto_action="REJECT",
                method="no_candidates",
                confidence=0.0,
            )

        # R0: Exact external ID match
        r0 = self._resolve_r0(candidates)
        if r0:
            return r0

        # R1: Deterministic crosswalk
        r1 = self._resolve_r1(candidates)
        if r1:
            return r1

        # R2: Normalized bibliographic composite
        r2 = self._resolve_r2(candidates)
        if r2:
            return r2

        # R3: High-confidence candidate (never auto-merge)
        r3 = self._resolve_r3(candidates)
        if r3:
            return r3

        # R4: Multi-source corroboration
        r4 = self._resolve_r4(candidates)
        if r4:
            return r4

        # R5: Human/scholar adjudication (always REVIEW)
        r5 = self._resolve_r5(candidates)
        if r5:
            return r5

        # No match found
        return ResolutionProposal(
            candidate_ids=[c.get("id", "") for c in candidates],
            auto_action="REVIEW",
            method="no_match",
            confidence=0.0,
        )

    def _resolve_r0(self, candidates: list[dict]) -> ResolutionProposal | None:
        """R0: Exact external ID match.

        If two candidates have the same external ID (e.g. both are GRETIL:xyz),
        they refer to the same entity.
        """
        id_groups: dict[str, list[str]] = {}
        for c in candidates:
            ext_ids = c.get("external_ids", [])
            for eid in ext_ids:
                scheme = eid.get("scheme", "")
                value = eid.get("value", "")
                key = f"{scheme}:{value}"
                if key in self._external_index:
                    # Found existing entity
                    entity_id = self._external_index[key]
                    return ResolutionProposal(
                        candidate_ids=[c.get("id", "") for c in candidates],
                        proposed_entity_id=entity_id,
                        relation="EXACT_IDENTITY",
                        method="R0_external_id",
                        confidence=1.0,
                        auto_action="MERGE",
                        feature_evidence={"external_id_match": key},
                    )
                id_groups.setdefault(key, []).append(c.get("id", ""))

        # Check if multiple candidates share an external ID
        for key, cids in id_groups.items():
            if len(cids) > 1:
                return ResolutionProposal(
                    candidate_ids=cids,
                    relation="EXACT_IDENTITY",
                    method="R0_shared_external_id",
                    confidence=1.0,
                    auto_action="MERGE",
                    feature_evidence={"shared_external_id": key},
                )

        return None

    def _resolve_r1(self, candidates: list[dict]) -> ResolutionProposal | None:
        """R1: Deterministic crosswalk.

        If we know that GRETIL:xyz = PANDiT:abc (via a mapping table),
        resolve directly.
        """
        # For now, check if candidates have cross-references
        for c in candidates:
            ext_ids = c.get("external_ids", [])
            for eid in ext_ids:
                scheme = eid.get("scheme", "")
                value = eid.get("value", "")
                # Check if this external ID maps to a known entity
                lookup_key = f"{scheme}:{value}"
                if lookup_key in self._external_index:
                    entity_id = self._external_index[lookup_key]
                    return ResolutionProposal(
                        candidate_ids=[c.get("id", "")],
                        proposed_entity_id=entity_id,
                        relation="PROBABLE_IDENTITY",
                        method="R1_crosswalk",
                        confidence=0.95,
                        auto_action="LINK_PROBABLE",
                        feature_evidence={"crosswalk_match": lookup_key},
                    )
        return None

    def _resolve_r2(self, candidates: list[dict]) -> ResolutionProposal | None:
        """R2: Normalized bibliographic composite.

        Compare title + author + edition/year using normalized fingerprints.
        """
        if len(candidates) < 2:
            return None

        # Build fingerprints for each candidate
        fingerprints: list[tuple[str, str]] = []
        for c in candidates:
            fp = self._compute_fingerprint(c)
            if fp:
                fingerprints.append((c.get("id", ""), fp))

        # Check for matching fingerprints
        fp_groups: dict[str, list[str]] = {}
        for cid, fp in fingerprints:
            fp_groups.setdefault(fp, []).append(cid)

        for fp, cids in fp_groups.items():
            if len(cids) > 1:
                # Check if fingerprint matches an existing entity
                existing = self._fingerprint_index.get(fp)
                return ResolutionProposal(
                    candidate_ids=cids,
                    proposed_entity_id=existing,
                    relation="PROBABLE_IDENTITY",
                    method="R2_bibliographic_composite",
                    confidence=0.85,
                    auto_action="REVIEW",
                    feature_evidence={
                        "fingerprint_match": fp,
                        "title_similarity": self._feature_evidence(candidates),
                    },
                )

        return None

    def _resolve_r3(self, candidates: list[dict]) -> ResolutionProposal | None:
        """R3: High-confidence candidate.

        Fuzzy matching — never auto-merge. Always requires review.
        """
        if len(candidates) < 2:
            return None

        # Simple title similarity for now
        best_pair = None
        best_score = 0.0

        for i, c1 in enumerate(candidates):
            for c2 in candidates[i+1:]:
                score = self._similarity_score(c1, c2)
                if score > best_score:
                    best_score = score
                    best_pair = (c1, c2)

        if best_pair and best_score > 0.7:
            return ResolutionProposal(
                candidate_ids=[best_pair[0].get("id", ""), best_pair[1].get("id", "")],
                relation="PROBABLE_IDENTITY",
                method="R3_fuzzy",
                confidence=best_score,
                auto_action="REVIEW",  # Never auto-merge at R3
                feature_evidence={
                    "similarity_score": best_score,
                    "title_similarity": self._feature_evidence(candidates),
                },
            )

        return None

    def _resolve_r4(self, candidates: list[dict]) -> ResolutionProposal | None:
        """R4: Multi-source corroboration.

        Per newbuildmainspec §45: Multiple independent sources confirm identity.
        Requires at least 2 independent sources with matching fingerprints.
        """
        if len(candidates) < 2:
            return None

        # Group candidates by source (provider_id)
        source_groups: dict[str, list[dict]] = {}
        for c in candidates:
            provider = c.get("provider_id", "unknown")
            source_groups.setdefault(provider, []).append(c)

        # Need at least 2 independent sources
        if len(source_groups) < 2:
            return None

        # Check if fingerprints match across sources
        fingerprints: list[tuple[str, str, str]] = []  # (candidate_id, fingerprint, source)
        for provider, group in source_groups.items():
            for c in group:
                fp = self._compute_fingerprint(c)
                if fp:
                    fingerprints.append((c.get("id", ""), fp, provider))

        # Group by fingerprint
        fp_groups: dict[str, list[tuple[str, str]]] = {}
        for cid, fp, source in fingerprints:
            fp_groups.setdefault(fp, []).append((cid, source))

        for fp, entries in fp_groups.items():
            sources = set(s for _, s in entries)
            if len(sources) >= 2:
                cids = [e[0] for e in entries]
                return ResolutionProposal(
                    candidate_ids=cids,
                    relation="PROBABLE_IDENTITY",
                    method="R4_multi_source",
                    confidence=0.9,
                    auto_action="LINK_PROBABLE",
                    feature_evidence={
                        "fingerprint_match": fp,
                        "independent_sources": list(sources),
                        "source_count": len(sources),
                    },
                )

        return None

    def _resolve_r5(self, candidates: list[dict]) -> ResolutionProposal | None:
        """R5: Human/scholar adjudication.

        Per newbuildmainspec §45: Always requires human review.
        This is a placeholder — actual adjudication comes from scholar attestations.
        """
        if len(candidates) < 2:
            return None

        # Check if any candidate has scholar attestations
        for c in candidates:
            if c.get("has_scholar_attestation"):
                return ResolutionProposal(
                    candidate_ids=[c.get("id", "") for c in candidates],
                    relation="PROBABLE_IDENTITY",
                    method="R5_scholar",
                    confidence=0.95,
                    auto_action="REVIEW",
                    feature_evidence={
                        "scholar_attestation": True,
                        "candidate_count": len(candidates),
                    },
                )

        return None

    def _compute_fingerprint(self, candidate: dict) -> str | None:
        """Compute a normalized fingerprint for bibliographic matching."""
        title = candidate.get("title", "").lower().strip()
        author = candidate.get("author", "").lower().strip()
        if not title:
            return None
        raw = f"{title}|{author}"
        return hashlib.sha256(raw.encode()).hexdigest()[:16]

    def _similarity_score(self, c1: dict, c2: dict) -> float:
        """Simple title similarity score."""
        t1 = (c1.get("title") or "").lower().strip()
        t2 = (c2.get("title") or "").lower().strip()
        if not t1 or not t2:
            return 0.0
        # Simple Jaccard similarity on words
        words1 = set(t1.split())
        words2 = set(t2.split())
        if not words1 or not words2:
            return 0.0
        intersection = words1 & words2
        union = words1 | words2
        return len(intersection) / len(union) if union else 0.0

    def _feature_evidence(self, candidates: list[dict]) -> dict:
        """Build feature evidence for the resolution proposal."""
        titles = [c.get("title", "") for c in candidates if c.get("title")]
        authors = [c.get("author", "") for c in candidates if c.get("author")]
        return {
            "titles": titles,
            "authors": authors,
            "count": len(candidates),
        }


if __name__ == "__main__":
    resolver = Resolver()

    # Register some existing entities
    resolver.register_entity("PTW_abc123", {"title": "Vigrahavyāvartanī", "author": "Nāgārjuna"})
    resolver.register_external_id("GRETIL", "sa_nAgArjuna-vigrahavyAvartanI", "PTW_abc123")

    # Test R0: exact external ID match
    candidates = [{
        "id": "PTCND_xyz",
        "title": "Vigrahavyāvartanī",
        "author": "Nāgārjuna",
        "external_ids": [{"scheme": "GRETIL", "value": "sa_nAgArjuna-vigrahavyAvartanI"}],
    }]

    proposal = resolver.resolve(candidates)
    print(f"Method: {proposal.method}")
    print(f"Confidence: {proposal.confidence}")
    print(f"Auto action: {proposal.auto_action}")
    print(f"Proposed entity: {proposal.proposed_entity_id}")
    print(f"Evidence: {proposal.feature_evidence}")
