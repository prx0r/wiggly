-- Migration 001: Create all v2 tables
-- Per newbuildmainspec OP1: schema foundation

BEGIN;

-- Entity identities (core)
CREATE TABLE IF NOT EXISTS entity_identity (
    id TEXT PRIMARY KEY,
    entity_class TEXT NOT NULL,
    created_event_id TEXT,
    lifecycle TEXT NOT NULL DEFAULT 'ACTIVE',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Events (append-only)
CREATE TABLE IF NOT EXISTS events (
    event_id TEXT PRIMARY KEY,
    event_type TEXT NOT NULL,
    stream_id TEXT,
    entity_ids TEXT[] NOT NULL,
    schema_uri TEXT NOT NULL,
    actor_id TEXT,
    occurred_at TIMESTAMPTZ,
    observed_at TIMESTAMPTZ,
    recorded_at TIMESTAMPTZ NOT NULL,
    payload JSONB NOT NULL,
    payload_digest JSONB NOT NULL,
    derivation_refs TEXT[],
    run_id TEXT,
    cursor SERIAL UNIQUE
);

-- Schema registry (append-only)
CREATE TABLE IF NOT EXISTS schema_registry (
    uri TEXT PRIMARY KEY,
    family TEXT NOT NULL,
    version TEXT NOT NULL,
    schema_dialect TEXT NOT NULL,
    artifact_id TEXT,
    digest_set JSONB NOT NULL,
    published_at TIMESTAMPTZ NOT NULL,
    supersedes TEXT,
    frozen BOOLEAN NOT NULL DEFAULT FALSE
);

-- Source providers
CREATE TABLE IF NOT EXISTS source_providers (
    id TEXT PRIMARY KEY,
    slug TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    homepage TEXT,
    provider_type TEXT NOT NULL,
    institution_id TEXT,
    trust_notes TEXT,
    default_rights_policy_id TEXT,
    status TEXT NOT NULL DEFAULT 'ACTIVE',
    discovered_at TIMESTAMPTZ NOT NULL,
    last_checked_at TIMESTAMPTZ
);

-- Source endpoints
CREATE TABLE IF NOT EXISTS source_endpoints (
    id TEXT PRIMARY KEY,
    provider_id TEXT NOT NULL REFERENCES source_providers(id),
    url TEXT NOT NULL,
    endpoint_type TEXT NOT NULL,
    adapter TEXT NOT NULL,
    capabilities TEXT[] NOT NULL,
    crawl_policy_id TEXT,
    status TEXT NOT NULL DEFAULT 'ACTIVE',
    last_checked_at TIMESTAMPTZ
);

-- Rights policies
CREATE TABLE IF NOT EXISTS rights_policies (
    id TEXT PRIMARY KEY,
    provider_id TEXT,
    resource_id TEXT,
    license_uri TEXT,
    copyright_status TEXT,
    discovery TEXT NOT NULL DEFAULT 'UNKNOWN',
    metadata_fetch TEXT NOT NULL DEFAULT 'UNKNOWN',
    content_fetch TEXT NOT NULL DEFAULT 'UNKNOWN',
    compute TEXT NOT NULL DEFAULT 'UNKNOWN',
    derivative_generation TEXT NOT NULL DEFAULT 'UNKNOWN',
    redistribution TEXT NOT NULL DEFAULT 'UNKNOWN',
    training TEXT NOT NULL DEFAULT 'UNKNOWN',
    evidence_refs TEXT[],
    reviewed_by TEXT,
    reviewed_at TIMESTAMPTZ
);

-- Artifacts (content-addressed)
CREATE TABLE IF NOT EXISTS artifacts (
    id TEXT PRIMARY KEY,
    digests JSONB NOT NULL,
    media_type TEXT NOT NULL,
    byte_length BIGINT NOT NULL,
    storage_uri TEXT,
    compression TEXT,
    encoding TEXT,
    rights_assessment_ids TEXT[],
    availability_state TEXT NOT NULL DEFAULT 'PRESENT',
    created_at TIMESTAMPTZ NOT NULL
);

-- Raw observations
CREATE TABLE IF NOT EXISTS raw_observations (
    id TEXT PRIMARY KEY,
    provider_id TEXT NOT NULL,
    endpoint_id TEXT NOT NULL,
    source_resource_id TEXT,
    requested_uri TEXT NOT NULL,
    resolved_uri TEXT,
    observed_at TIMESTAMPTZ NOT NULL,
    response_metadata_artifact TEXT,
    payload_artifact_id TEXT NOT NULL,
    rights_assessment_id TEXT NOT NULL,
    run_id TEXT,
    source_state JSONB,
    status TEXT NOT NULL DEFAULT 'FETCHED'
);

-- Entity candidates
CREATE TABLE IF NOT EXISTS entity_candidates (
    id TEXT PRIMARY KEY,
    candidate_type TEXT NOT NULL,
    provider_id TEXT NOT NULL,
    external_resource_id TEXT,
    assertion_ids TEXT[] NOT NULL,
    normalized_fingerprint TEXT,
    created_at TIMESTAMPTZ NOT NULL
);

-- Candidate assertions
CREATE TABLE IF NOT EXISTS candidate_assertions (
    id TEXT PRIMARY KEY,
    observation_id TEXT NOT NULL,
    subject_candidate_id TEXT,
    predicate TEXT NOT NULL,
    value TEXT,
    object_id TEXT,
    source_selector JSONB,
    extraction_method TEXT NOT NULL,
    extractor_version TEXT NOT NULL,
    confidence REAL,
    created_at TIMESTAMPTZ NOT NULL
);

-- Assertions (canonical, resolved)
CREATE TABLE IF NOT EXISTS assertions (
    id TEXT PRIMARY KEY,
    subject_id TEXT NOT NULL,
    predicate_uri TEXT NOT NULL,
    object_id TEXT,
    literal TEXT,
    epistemic_mode TEXT NOT NULL,
    evidence_use_ids TEXT[] NOT NULL DEFAULT '{}',
    asserted_by TEXT NOT NULL,
    actor_ref TEXT,
    asserted_at TIMESTAMPTZ,
    recorded_at TIMESTAMPTZ NOT NULL,
    lifecycle TEXT NOT NULL DEFAULT 'ACTIVE',
    created_from_event TEXT NOT NULL,
    supersedes TEXT
);

-- External identifiers
CREATE TABLE IF NOT EXISTS external_identifiers (
    id TEXT PRIMARY KEY,
    entity_id TEXT NOT NULL,
    scheme TEXT NOT NULL,
    value TEXT NOT NULL,
    source_observation_id TEXT,
    relation_confidence REAL,
    created_at TIMESTAMPTZ NOT NULL
);

-- Identity assertions
CREATE TABLE IF NOT EXISTS identity_assertions (
    id TEXT PRIMARY KEY,
    subject_id TEXT NOT NULL,
    object_id TEXT NOT NULL,
    relation TEXT NOT NULL,
    evidence_refs TEXT[] NOT NULL,
    asserted_by TEXT NOT NULL,
    confidence REAL,
    review_state TEXT NOT NULL DEFAULT 'PENDING',
    created_at TIMESTAMPTZ NOT NULL
);

-- Identity merges
CREATE TABLE IF NOT EXISTS identity_merges (
    id TEXT PRIMARY KEY,
    from_ids TEXT[] NOT NULL,
    into_id TEXT NOT NULL,
    evidence TEXT NOT NULL,
    event_id TEXT NOT NULL,
    performed_by TEXT
);

-- Identity splits
CREATE TABLE IF NOT EXISTS identity_splits (
    id TEXT PRIMARY KEY,
    old_id TEXT NOT NULL,
    new_ids TEXT[] NOT NULL,
    allocation_evidence TEXT NOT NULL,
    unresolved_members TEXT[],
    event_id TEXT NOT NULL
);

-- Ledger checkpoints
CREATE TABLE IF NOT EXISTS ledger_checkpoints (
    id TEXT PRIMARY KEY,
    previous_checkpoint_id TEXT,
    first_event_cursor INTEGER NOT NULL,
    last_event_cursor INTEGER NOT NULL,
    event_count INTEGER NOT NULL,
    merkle JSONB NOT NULL,
    generated_at TIMESTAMPTZ NOT NULL,
    signatures JSONB NOT NULL DEFAULT '[]'
);

-- Derived tables (projections)

-- Works
CREATE TABLE IF NOT EXISTS works (
    id TEXT PRIMARY KEY,
    preferred_title TEXT NOT NULL DEFAULT '',
    work_type TEXT NOT NULL DEFAULT 'TEXT',
    current_title_assertion_id TEXT,
    external_ids JSONB NOT NULL DEFAULT '[]',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- People
CREATE TABLE IF NOT EXISTS people (
    id TEXT PRIMARY KEY,
    preferred_name TEXT NOT NULL DEFAULT '',
    external_ids JSONB NOT NULL DEFAULT '[]',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Institutions
CREATE TABLE IF NOT EXISTS institutions (
    id TEXT PRIMARY KEY,
    preferred_name TEXT NOT NULL DEFAULT '',
    external_ids JSONB NOT NULL DEFAULT '[]',
    location TEXT,
    homepage TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Editions
CREATE TABLE IF NOT EXISTS editions (
    id TEXT PRIMARY KEY,
    work_id TEXT REFERENCES works(id),
    title TEXT NOT NULL DEFAULT '',
    publication_assertions JSONB NOT NULL DEFAULT '[]',
    editor_assertions JSONB NOT NULL DEFAULT '[]',
    publisher_assertions JSONB NOT NULL DEFAULT '[]',
    year_assertions JSONB NOT NULL DEFAULT '[]',
    external_ids JSONB NOT NULL DEFAULT '[]',
    rights_policy_id TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Witnesses
CREATE TABLE IF NOT EXISTS witnesses (
    id TEXT PRIMARY KEY,
    work_id TEXT REFERENCES works(id),
    holding_institution_id TEXT,
    shelfmark TEXT,
    material_type TEXT,
    external_ids JSONB NOT NULL DEFAULT '[]',
    assertion_ids JSONB NOT NULL DEFAULT '[]',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ETexts
CREATE TABLE IF NOT EXISTS etexts (
    id TEXT PRIMARY KEY,
    work_id TEXT REFERENCES works(id),
    edition_id TEXT,
    witness_id TEXT,
    provider_id TEXT NOT NULL,
    artifact_id TEXT NOT NULL,
    text_format TEXT NOT NULL DEFAULT 'PLAIN',
    script TEXT NOT NULL DEFAULT 'devanagari',
    language TEXT NOT NULL DEFAULT 'san',
    derivation_assertions JSONB NOT NULL DEFAULT '[]',
    quality_state TEXT NOT NULL DEFAULT 'UNKNOWN',
    rights_policy_id TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Translations
CREATE TABLE IF NOT EXISTS translations (
    id TEXT PRIMARY KEY,
    work_id TEXT REFERENCES works(id),
    target_language TEXT NOT NULL DEFAULT 'eng',
    translator_ids TEXT[] NOT NULL DEFAULT '{}',
    publication_id TEXT,
    source_edition_id TEXT,
    source_etext_id TEXT,
    completeness TEXT NOT NULL DEFAULT 'UNKNOWN',
    rights_policy_id TEXT,
    external_ids JSONB NOT NULL DEFAULT '[]',
    provenance_refs TEXT[] NOT NULL DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Passages
CREATE TABLE IF NOT EXISTS passages (
    id TEXT PRIMARY KEY,
    work_id TEXT NOT NULL,
    citation_scheme TEXT NOT NULL DEFAULT '',
    citation_value TEXT NOT NULL DEFAULT '',
    parent_passage_id TEXT,
    order_key TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

COMMIT;
