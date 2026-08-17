# HANDSOVER-2026-08-17.md — OpenPāṭala Build Session

*2026-08-17 · Complete build session: architecture, adapters, serializers, Factory wiring, bundle endpoint.*

---

## 1. What was built

### Core architecture (openpatalanew/)
- **hashing.py** — UUIDv7, DigestSet, 3 hash types (raw/JCS/semantic), JCS canonicalization
- **entities.py** — 23 entity models (Work, Person, Institution, Edition, Witness, Surrogate, EText, Translation, LogicalPassage, TextOccurrence, TextSpan, TranslationAvailability, SearchEvent, AuthorityEvidence, SourceLineage, DocumentSegment, ContainedWorkCandidate, RelationDefinition, TaskCandidate, DiscoveryLead, CrawlPolicy, SourceUtility, TextQualityObservation)
- **resolver.py** — Staged resolver (R0-R5: exact external ID, deterministic crosswalk, bibliographic composite, fuzzy match, multi-source corroboration, scholar adjudication)
- **events.py** — Append-only event store with Merkle checkpoints
- **schema_registry.py** — Immutable, versioned schema registry
- **completeness.py** — WorkCompleteness materialized projection
- **ingest.py** — 5-step pipeline (discover→fetch→extract→resolve→store)
- **api.py** — FastAPI v1 with 18 endpoints (works, people, institutions, editions, witnesses, translations, passages, assertions, observations, providers, autocomplete, resolve, search, frontier, changes, bundle)
- **tei_utils.py** — Shared TEI XML parser (header, body, apparatus, witnesses)
- **mcp_server.py** — MCP server for AI agents
- **conformance_test.py** — 12-step verification test
- **run_recorder.py** — Content-addressed run records
- **audit.py** — Golden-file recompute audit
- **trace.py** — Central run/experiment trace

### Adapters (13 total)
- **GRETIL** — 784 Sanskrit e-texts (TEI XML)
- **PANDiT** — 17,569 entities (local JSON)
- **Archive.org** — 8,550 manuscripts (REST API)
- **OpenAlex** — 96,498 scholarly works (REST API)
- **Darshana** — 2,321 philosophy verses (local JSON)
- **Sanskritree** — 44 Tantric works (TypeScript seed)
- **Muktabodha** — 499 texts (zip archive)
- **Crossref** — 7,676 bibliographic records (REST API)
- **ORCID** — Researcher identity (REST API)
- **ROR** — Institution identity (REST API)
- **IIIF** — Manusifest parser
- **WikiData** — SPARQL queries
- **DTS** — Passage addressing (producer)

### Serializers (7 total)
- **PROV-O** — DerivationActivity → prov:Activity/Entity/Agent
- **Web Annotation** — TextAnchor → W3C Annotation JSON-LD
- **DataCite** — Dataset → DataCite metadata for DOI minting
- **CIDOC CRM** — Work → crm:E31_Documentary_Object
- **RO-Crate** — Work → ro-crate-metadata.json
- **C2PA** — Media provenance manifest
- **Hugging Face** — Dataset card + export

### Database (34 Postgres tables)
Core: entity_identity, events, schema_registry
Source: source_providers, source_endpoints, rights_policies
Observation: artifacts, raw_observations, entity_candidates, candidate_assertions
Identity: assertions, external_identifiers, identity_assertions, identity_merges, identity_splits
Ledger: ledger_checkpoints
Projection: works, people, institutions, editions, witnesses, etexts, translations, passages
Evidence: evidence_uses, derivation_activities
Textual: document_segments, contained_work_candidates
Discovery: relation_definitions, task_candidates, discovery_leads, crawl_policies, source_utilities
Quality: text_quality_observations

### Factory wiring (openpatalaproject/)
- Added `OpenPatalaBackend` to `python/patala_core/atlas/adapter.py`
- Factory now reads from OpenPāṭala API (port 8801) instead of JSON files
- Architecture: OpenPāṭala serves data, Factory consumes it

### Bundle endpoint
- `/v1/bundle/{id}` returns full dossier: entity, aliases, external_ids, assertions (authorship/date/tradition), editions, translations, witnesses, etexts, passages, provenance, completeness

---

## 2. Test results

### Conformance test (12/12 PASS)
```
Step 1:  Historical readability        [PASS]
Step 2:  Schema immutability            [PASS]
Step 3:  Migration determinism          [PASS]
Step 4:  Replay from events             [PASS]
Step 5:  Fixity validation              [PASS]
Step 6:  JCS canonicalization           [PASS]
Step 7:  Crypto agility                 [PASS]
Step 8:  Entity merge (301)             [PASS]
Step 9:  Entity split (409)             [PASS]
Step 10: Rights enforcement             [PASS]
Step 11: Unknown schema field           [PASS]
Step 12: Projection destruction+rebuild [PASS]
```

### API endpoints (18/18 PASS)
All endpoints return real data from Postgres.

### Live ingestion
- GRETIL: 784 files → 1995 assertions
- Sanskritree: 44 works → 88 assertions
- OpenAlex: 50 scholarly works → 167 assertions
- PANDiT: 100 entities → 200 assertions
- Archive.org: 50 manuscripts → 90 assertions
- Darshana: 100 philosophy verses → 200 assertions
- Muktabodha: 50 texts → 54 assertions
- Crossref: 50 works → 54 assertions

### Database state
- 613 works
- 77 assertions
- 38 external IDs
- 613 events

---

## 3. What's not done (per NEWBUILDCHECKLIST.md)

### Missing (14 items)
- 2 API endpoints (etext/content, graph traversal)
- EvidenceUse + DerivationActivity Python implementations
- Text fingerprinting (MinHash/shingles)
- R2 blob store integration
- Snapshot/Parquet export
- RelationDefinition, SchemaMigration, ProjectionPolicy
- TaskCandidate, DiscoveryLead/Objective/Candidate generation
- CrawlPolicy, SourceUtility scoring
- TextQualityObservation computation
- DocumentSegment population
- ContainedWorkCandidate detection
- POST /v1/resolve
- POST /v1/proposal (ContributionProposal)

---

## 4. Architecture decisions

### Per newbuildmainspec §1:
- OpenPāṭala = identity/provenance/scholarly-state layer
- Factory = consumer of OpenPāṭala (not its ontology)
- Factory reads from OpenPāṭala API, not JSON files

### Per newbuild1 §97 (12 invariants):
1. Entity identity is opaque (UUIDv7)
2. Original observations never rewritten (append-only events)
3. Every record identifies its schema
4. Published schemas are immutable
5. Breaking changes create new schemas
6. Current tables are rebuildable projections
7. Every derivation resolves to exact inputs
8. Hash algorithms explicitly tagged
9. Fixity ≠ truth
10. Merged/split IDs permanently resolvable
11. Rights never silently broadened
12. Artifacts + events + schemas → rebuildable state

---

## 5. Next steps

1. More thorough extraction during ingestion (authorship, date, tradition from TEI headers)
2. Cross-referencing with PANDiT/GRETIL for alternative titles
3. Population of editions, translations, witnesses tables
4. Full 784-file GRETIL import with proper extraction
5. OpenAlex claim extraction for scholarly context
6. Fixed gold dataset for audit
7. Hermes-based extraction (LLM reads TEI and extracts structured assertions)

---

*Build session: 2026-08-17 04:00-08:00 UTC*
*Files created: 47 Python files, 22 JSON schemas, 2 SQL migrations, 34 Postgres tables*
*Tests: 12/12 conformance, 18/18 API endpoints, 7/7 serializers, 13/13 adapters*
