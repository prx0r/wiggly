-- Migration 002: Add missing tables + columns
-- EvidenceUse, DerivationActivity, DocumentSegment, ContainedWorkCandidate
-- RelationDefinition, TaskCandidate, DiscoveryLead, CrawlPolicy, SourceUtility
-- TextQualityObservation

BEGIN;

-- EvidenceUse
CREATE TABLE IF NOT EXISTS evidence_uses (
    id TEXT PRIMARY KEY,
    assertion_id TEXT NOT NULL,
    evidence_entity_id TEXT NOT NULL,
    role TEXT NOT NULL,
    anchor_id TEXT,
    interpretation_note TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- DerivationActivity
CREATE TABLE IF NOT EXISTS derivation_activities (
    id TEXT PRIMARY KEY,
    activity_type TEXT NOT NULL,
    inputs JSONB NOT NULL DEFAULT '[]',
    outputs JSONB NOT NULL DEFAULT '[]',
    actor_id TEXT,
    software JSONB,
    configuration JSONB,
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    run_id TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- DocumentSegment
CREATE TABLE IF NOT EXISTS document_segments (
    id TEXT PRIMARY KEY,
    etext_id TEXT NOT NULL,
    parent_id TEXT,
    segment_type TEXT NOT NULL DEFAULT 'UNKNOWN',
    ordinal INTEGER NOT NULL DEFAULT 0,
    text TEXT NOT NULL DEFAULT '',
    locator TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ContainedWorkCandidate
CREATE TABLE IF NOT EXISTS contained_work_candidates (
    id TEXT PRIMARY KEY,
    observation_id TEXT NOT NULL,
    work_candidate TEXT NOT NULL,
    start_locator TEXT,
    end_locator TEXT,
    detection_method TEXT,
    evidence TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- RelationDefinition (versioned relation vocabulary)
CREATE TABLE IF NOT EXISTS relation_definitions (
    uri TEXT PRIMARY KEY,
    version TEXT NOT NULL,
    domain TEXT[] NOT NULL DEFAULT '{}',
    range TEXT[] NOT NULL DEFAULT '{}',
    semantics TEXT NOT NULL DEFAULT '',
    inverse TEXT,
    transitive BOOLEAN DEFAULT FALSE,
    staleness_policy TEXT,
    authority_policy TEXT,
    deprecated BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- TaskCandidate
CREATE TABLE IF NOT EXISTS task_candidates (
    id TEXT PRIMARY KEY,
    task_type TEXT NOT NULL,
    target_id TEXT NOT NULL,
    priority REAL NOT NULL DEFAULT 0.0,
    reason TEXT NOT NULL DEFAULT '',
    status TEXT NOT NULL DEFAULT 'PENDING',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- DiscoveryLead
CREATE TABLE IF NOT EXISTS discovery_leads (
    id TEXT PRIMARY KEY,
    source_observation TEXT NOT NULL,
    target_type TEXT NOT NULL,
    candidate_url TEXT,
    candidate_name TEXT,
    reason TEXT NOT NULL DEFAULT '',
    priority REAL NOT NULL DEFAULT 0.0,
    status TEXT NOT NULL DEFAULT 'PROPOSED',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- CrawlPolicy
CREATE TABLE IF NOT EXISTS crawl_policies (
    id TEXT PRIMARY KEY,
    provider_id TEXT NOT NULL,
    robots_behavior TEXT DEFAULT 'respect',
    max_requests_per_second REAL DEFAULT 1.0,
    max_concurrency INTEGER DEFAULT 1,
    allowed_paths TEXT[] DEFAULT '{}',
    denied_paths TEXT[] DEFAULT '{}',
    metadata_only BOOLEAN DEFAULT TRUE,
    content_fetch_allowed BOOLEAN DEFAULT FALSE,
    max_resource_bytes BIGINT DEFAULT 10485760,
    backoff_policy TEXT DEFAULT 'exponential',
    contact_email TEXT,
    terms_review_ref TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- SourceUtility
CREATE TABLE IF NOT EXISTS source_utilities (
    id TEXT PRIMARY KEY,
    provider_id TEXT NOT NULL,
    novelty_yield REAL DEFAULT 0.0,
    works_per_request REAL DEFAULT 0.0,
    source_quality REAL DEFAULT 0.0,
    rights_clarity REAL DEFAULT 0.0,
    structuredness REAL DEFAULT 0.0,
    authority_value REAL DEFAULT 0.0,
    target_gap_match REAL DEFAULT 0.0,
    acquisition_cost REAL DEFAULT 0.0,
    failure_rate REAL DEFAULT 0.0,
    computed_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- TextQualityObservation
CREATE TABLE IF NOT EXISTS text_quality_observations (
    id TEXT PRIMARY KEY,
    target_artifact_id TEXT NOT NULL,
    metric TEXT NOT NULL,
    value REAL NOT NULL,
    method TEXT NOT NULL,
    sample_scope TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Add missing columns to existing tables
ALTER TABLE works ADD COLUMN IF NOT EXISTS state_cursor SERIAL;
ALTER TABLE people ADD COLUMN IF NOT EXISTS schema_uri TEXT DEFAULT 'https://patala.org/schemas/v2/person.json';
ALTER TABLE institutions ADD COLUMN IF NOT EXISTS schema_uri TEXT DEFAULT 'https://patala.org/schemas/v2/institution.json';
ALTER TABLE editions ADD COLUMN IF NOT EXISTS schema_uri TEXT DEFAULT 'https://patala.org/schemas/v2/edition.json';
ALTER TABLE translations ADD COLUMN IF NOT EXISTS schema_uri TEXT DEFAULT 'https://patala.org/schemas/v2/translation.json';

COMMIT;
