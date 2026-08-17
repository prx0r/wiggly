#!/usr/bin/env python3
"""patala/entities.py — minimal entity models for OpenPāṭala.

Per newbuildmainspec §11-23:
- Work is deliberately small (preferred_title is a projection, not intrinsic truth)
- All other fields (author, date, tradition) are assertions, not columns
- Translation is a separate entity type, not an edition variant

"Tools don't become truth. Their outputs become observations." — newbuild
"""
from __future__ import annotations

import sys
from dataclasses import dataclass, field
from typing import Any

sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parents[1]))
from patala.hashing import uuid7


@dataclass
class Work:
    """Canonical Work — deliberately minimal.

    Per newbuildmainspec §11: "Keep Work deliberately small.
    Do not store directly: author, date, tradition, school.
    Those are scholarly assertions."
    """
    id: str = ""
    preferred_title: str = ""  # computed projection, not intrinsic truth
    work_type: str = "TEXT"  # TEXT | COMMENTARY | TANTRA | SUTRA | ...
    current_title_assertion_id: str | None = None
    external_ids: list[dict] = field(default_factory=list)
    created_at: str = ""

    def __post_init__(self):
        if not self.id:
            self.id = f"PTW_{uuid7()}"


@dataclass
class Person:
    """A person (author, scholar, translator)."""
    id: str = field(default_factory=lambda: f"PTP_{uuid7()}")
    preferred_name: str = ""
    external_ids: list[dict] = field(default_factory=list)  # ORCID, PANDiT, etc.
    created_at: str = ""


@dataclass
class Institution:
    """An institution (publisher, library, university)."""
    id: str = field(default_factory=lambda: f"PTINST_{uuid7()}")
    preferred_name: str = ""
    external_ids: list[dict] = field(default_factory=list)  # ROR, etc.
    location: str | None = None
    homepage: str | None = None


@dataclass
class Edition:
    """A published edition of a work."""
    id: str = field(default_factory=lambda: f"PTED_{uuid7()}")
    work_id: str | None = None
    title: str = ""
    publication_assertions: list[dict] = field(default_factory=list)
    editor_assertions: list[dict] = field(default_factory=list)
    publisher_assertions: list[dict] = field(default_factory=list)
    year_assertions: list[dict] = field(default_factory=list)
    external_ids: list[dict] = field(default_factory=list)
    rights_policy_id: str | None = None


@dataclass
class Witness:
    """A physical manuscript witness."""
    id: str = field(default_factory=lambda: f"PTMS_{uuid7()}")
    work_id: str | None = None
    holding_institution_id: str | None = None
    shelfmark: str | None = None
    material_type: str | None = None  # palm_leaf | paper | microfilm | ...
    external_ids: list[dict] = field(default_factory=list)
    assertion_ids: list[dict] = field(default_factory=list)


@dataclass
class Surrogate:
    """A digital surrogate of a witness (scan, photo, IIIF)."""
    id: str = field(default_factory=lambda: f"PTSRG_{uuid7()}")
    witness_id: str | None = None
    provider_id: str = ""
    manifestation_type: str = "SCAN"  # SCAN | PHOTO | MICROFILM | IIIF
    artifact_refs: list[str] = field(default_factory=list)
    iiif_manifest: str | None = None
    rights_policy_id: str = ""


@dataclass
class EText:
    """A machine-readable text (TEI, plain, etc.)."""
    id: str = field(default_factory=lambda: f"PTTX_{uuid7()}")
    work_id: str | None = None
    edition_id: str | None = None
    witness_id: str | None = None
    provider_id: str = ""
    artifact_id: str = ""
    text_format: str = "PLAIN"  # PLAIN | TEI | XML | JSON | HTML
    script: str = "devanagari"
    language: str = "san"
    derivation_assertions: list[dict] = field(default_factory=list)
    quality_state: str = "UNKNOWN"  # UNKNOWN | RAW | OCR | CLEAN | SCHOLARLY
    rights_policy_id: str = ""


@dataclass
class Translation:
    """A translation of a work.

    Per newbuildmainspec §22: "Translation existence is a canonical entity state,
    not a boolean. Translation must not simply be another edition_type."
    """
    id: str = field(default_factory=lambda: f"PTTR_{uuid7()}")
    work_id: str | None = None
    target_language: str = "eng"
    translator_ids: list[str] = field(default_factory=list)
    publication_id: str | None = None
    source_edition_id: str | None = None
    source_etext_id: str | None = None
    completeness: str = "UNKNOWN"  # FULL | PARTIAL | EXCERPT | UNKNOWN
    rights_policy_id: str = ""
    external_ids: list[dict] = field(default_factory=list)
    provenance_refs: list[str] = field(default_factory=list)


@dataclass
class LogicalPassage:
    """A logical citation (e.g. Tantrāloka 3.17)."""
    id: str = field(default_factory=lambda: f"PTPASS_{uuid7()}")
    work_id: str = ""
    citation_scheme: str = ""  # e.g. "chapter.verse"
    citation_value: str = ""  # e.g. "3.17"
    parent_passage_id: str | None = None
    order_key: str | None = None


@dataclass
class TextOccurrence:
    """A textual occurrence in a specific carrier (edition, manuscript, etc.).

    Per newbuildmainspec §20: Separates logical citation from occurrence.
    """
    id: str = field(default_factory=lambda: f"PTTOC_{uuid7()}")
    logical_passage_id: str | None = None
    carrier_type: str = "ETEXT"  # ETEXT | EDITION | WITNESS | TRANSLATION
    carrier_id: str = ""
    locator: str = ""
    exact_text: str = ""
    text_hash: str = ""
    language: str = "san"
    script: str = "devanagari"


@dataclass
class TextSpan:
    """A selector pointing to exact text in a source.

    Per newbuild1 §43: 'Use multiple selectors. W3C Web Annotation model.'
    """
    id: str = field(default_factory=lambda: f"PTSPAN_{uuid7()}")
    occurrence_id: str = ""
    selector_type: str = "CHAR_OFFSET"  # CHAR_OFFSET | TOKEN_RANGE | LINE_RANGE | XML_ID | XPATH | IIIF_REGION
    start: int | None = None
    end: int | None = None
    selector_payload: dict = field(default_factory=dict)


@dataclass
class TranslationAvailability:
    """Projection of translation availability per work.

    Per newbuildmainspec §24: Projection, not primary truth.
    """
    work_id: str = ""
    state: str = "NONE_KNOWN"  # NONE_KNOWN | PARTIAL | FULL | MULTIPLE | UNKNOWN
    translations: list[str] = field(default_factory=list)
    english_state: str = "NONE_KNOWN"
    searched_at: str = ""
    search_coverage: str = ""
    unresolved_candidates: list[str] = field(default_factory=list)
    patala_factory_eligible: bool = False


@dataclass
class SearchEvent:
    """A record of what was searched and what was found.

    Per newbuildmainspec §25: 'Pāṭala searched these sources and found none.'
    """
    id: str = field(default_factory=lambda: f"PTSE_{uuid7()}")
    query_type: str = "TRANSLATION"  # TRANSLATION | WORK | EDITION | WITNESS | SOURCE
    target_id: str | None = None
    query_terms: list[str] = field(default_factory=list)
    providers_searched: list[str] = field(default_factory=list)
    started_at: str = ""
    completed_at: str = ""
    results: list[str] = field(default_factory=list)
    method_version: str = ""
    coverage_estimate: str | None = None
    outcome: str = "NO_MATCH"  # FOUND | NO_MATCH | PARTIAL | FAILED


@dataclass
class AuthorityEvidence:
    """Multi-dimensional authority for an entity's properties.

    Per newbuildmainspec §29: 'Do not collapse into verified=true.'
    """
    id: str = field(default_factory=lambda: f"PTAUTH_{uuid7()}")
    subject_id: str = ""
    dimension: str = ""  # WORK_IDENTITY | AUTHOR_IDENTITY | EDITION_IDENTITY | ETEXT_DERIVATION | ...
    state: str = ""
    evidence_refs: list[str] = field(default_factory=list)
    source_independence_class: str = ""  # INDEPENDENT | COPIED | UNKNOWN
    asserted_at: str = ""


@dataclass
class SourceLineage:
    """Relationship between two data sources (independent vs copied).

    Per newbuildmainspec §30: '3 catalogues can be one epistemic source copied three times.'
    """
    source_a: str = ""
    source_b: str = ""
    relationship: str = "UNKNOWN"  # INDEPENDENT | COPIED_FROM | MIRROR_OF | DERIVED_FROM | UNKNOWN


@dataclass
class DocumentSegment:
    """A segment of a document (chapter, section, verse, prose).

    Per newbuildmainspec §49: 'Huge improvement over the current verse-first worldview.'
    """
    id: str = field(default_factory=lambda: f"PTSEG_{uuid7()}")
    etext_id: str = ""
    parent_id: str | None = None
    segment_type: str = "UNKNOWN"  # WORK | CHAPTER | SECTION | VERSE | PROSE | COLOPHON | COMMENTARY | HEADER | FOOTNOTE | UNKNOWN
    ordinal: int = 0
    text: str = ""
    locator: str = ""


@dataclass
class ContainedWorkCandidate:
    """A work candidate found within a larger resource.

    Per newbuildmainspec §48: 'One archive item may contain multiple works.'
    """
    id: str = field(default_factory=lambda: f"PTCWC_{uuid7()}")
    observation_id: str = ""
    work_candidate: str = ""
    start_locator: str = ""
    end_locator: str = ""
    detection_method: str = ""
    evidence: str = ""


@dataclass
class RelationDefinition:
    """Versioned relation vocabulary.

    Per newbuild1 §54-55: 'The meaning of edges must be versionable too.'
    """
    uri: str = ""
    version: str = "1.0.0"
    domain: list[str] = field(default_factory=list)
    range: list[str] = field(default_factory=list)
    semantics: str = ""
    inverse: str | None = None
    transitive: bool = False
    staleness_policy: str | None = None
    authority_policy: str | None = None
    deprecated: bool = False


@dataclass
class TaskCandidate:
    """A generated work item from gap analysis.

    Per newbuildmainspec §43: 'if work.source == NONE: emit FIND_SOURCE'
    """
    id: str = field(default_factory=lambda: f"PTTASK_{uuid7()}")
    task_type: str = ""  # FIND_SOURCE | RESOLVE_IDENTITY | SEARCH_TRANSLATION | TRANSLATE | RESOLVE_RIGHTS
    target_id: str = ""
    priority: float = 0.0
    reason: str = ""
    status: str = "PENDING"  # PREADY | IN_PROGRESS | COMPLETED | FAILED


@dataclass
class DiscoveryLead:
    """A lead for discovering new sources.

    Per newbuildmainspec §34: 'Every observed item can contain leads.'
    """
    id: str = field(default_factory=lambda: f"PTDL_{uuid7()}")
    source_observation: str = ""
    target_type: str = ""
    candidate_url: str | None = None
    candidate_name: str | None = None
    reason: str = ""
    priority: float = 0.0
    status: str = "PROPOSED"  # PROPOSED | POLICY_CHECK | TESTED | ADOPTED | REJECTED


@dataclass
class CrawlPolicy:
    """Per-source crawl configuration.

    Per newbuildmainspec §39: 'Respect site rules/terms.'
    """
    id: str = field(default_factory=lambda: f"PTCP_{uuid7()}")
    provider_id: str = ""
    robots_behavior: str = "respect"
    max_requests_per_second: float = 1.0
    max_concurrency: int = 1
    allowed_paths: list[str] = field(default_factory=list)
    denied_paths: list[str] = field(default_factory=list)
    metadata_only: bool = True
    content_fetch_allowed: bool = False
    max_resource_bytes: int = 10 * 1024 * 1024  # 10MB default
    backoff_policy: str = "exponential"
    contact_email: str | None = None
    terms_review_ref: str | None = None


@dataclass
class SourceUtility:
    """Scoring for source discovery prioritization.

    Per newbuildmainspec §40: 'GapValue × ExpectedYield × SourceAuthority × RightsUsability × DownstreamReach / Cost'
    """
    id: str = field(default_factory=lambda: f"PTSU_{uuid7()}")
    provider_id: str = ""
    novelty_yield: float = 0.0
    works_per_request: float = 0.0
    source_quality: float = 0.0
    rights_clarity: float = 0.0
    structuredness: float = 0.0
    authority_value: float = 0.0
    target_gap_match: float = 0.0
    acquisition_cost: float = 0.0
    failure_rate: float = 0.0


@dataclass
class TextQualityObservation:
    """Quality metric for a text artifact.

    Per newbuildmainspec §51: 'Do not put ocr_needs_correction = True as the main ontology.'
    """
    id: str = field(default_factory=lambda: f"PTTQO_{uuid7()}")
    target_artifact_id: str = ""
    metric: str = ""  # OCR_QUALITY | TEXT_CLEANLINESS | ENCODING_CORRECTNESS
    value: float = 0.0
    method: str = ""
    sample_scope: str = ""


# Entity class → prefix mapping
ENTITY_PREFIXES = {
    "WORK": "PTW",
    "PERSON": "PTP",
    "INSTITUTION": "PTINST",
    "EDITION": "PTED",
    "WITNESS": "PTMS",
    "SURROGATE": "PTSRG",
    "ETEXT": "PTTX",
    "TRANSLATION": "PTTR",
    "PASSAGE": "PTPASS",
    "TEXT_OCCURRENCE": "PTTOC",
    "TEXT_SPAN": "PTSPAN",
    "SEARCH_EVENT": "PTSE",
    "DOCUMENT_SEGMENT": "PTSEG",
    "CONTAINED_WORK_CANDIDATE": "PTCWC",
    "RELATION_DEFINITION": "PTRD",
    "TASK_CANDIDATE": "PTTASK",
    "DISCOVERY_LEAD": "PTDL",
    "CRAWL_POLICY": "PTCP",
    "SOURCE_UTILITY": "PTSU",
    "TEXT_QUALITY_OBSERVATION": "PTTQO",
}

# Entity class → dataclass mapping
ENTITY_CLASSES = {
    "WORK": Work,
    "PERSON": Person,
    "INSTITUTION": Institution,
    "EDITION": Edition,
    "WITNESS": Witness,
    "SURROGATE": Surrogate,
    "ETEXT": EText,
    "TRANSLATION": Translation,
    "PASSAGE": LogicalPassage,
    "TEXT_OCCURRENCE": TextOccurrence,
    "TEXT_SPAN": TextSpan,
    "TRANSLATION_AVAILABILITY": TranslationAvailability,
    "SEARCH_EVENT": SearchEvent,
    "AUTHORITY_EVIDENCE": AuthorityEvidence,
    "SOURCE_LINEAGE": SourceLineage,
    "DOCUMENT_SEGMENT": DocumentSegment,
    "CONTAINED_WORK_CANDIDATE": ContainedWorkCandidate,
    "RELATION_DEFINITION": RelationDefinition,
    "TASK_CANDIDATE": TaskCandidate,
    "DISCOVERY_LEAD": DiscoveryLead,
    "CRAWL_POLICY": CrawlPolicy,
    "SOURCE_UTILITY": SourceUtility,
    "TEXT_QUALITY_OBSERVATION": TextQualityObservation,
}


def create_entity(entity_class: str, **kwargs) -> Any:
    """Factory function to create an entity by class name."""
    cls = ENTITY_CLASSES.get(entity_class)
    if not cls:
        raise ValueError(f"Unknown entity class: {entity_class}")
    return cls(**kwargs)


if __name__ == "__main__":
    print("=== Entity Models ===")
    for cls_name, cls in ENTITY_CLASSES.items():
        e = cls()
        print(f"  {cls_name}: {e.id}")

    print()
    print("=== Factory ===")
    w = create_entity("WORK", preferred_title="Vigrahavyāvartanī")
    print(f"Work: {w.id} — {w.preferred_title}")
