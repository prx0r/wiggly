# HANDSOVER-2026-08-17.md — Complete Session Handover

*2026-08-17T14:45:00Z · Full handover: architecture, adapters, proofs, evidence, phases 0.6 + 1.0.*

---

## 1. WHAT WAS BUILT

### Core Architecture (patala/)

| Module | Purpose | Lines |
|---|---|---|
| `hashing.py` | UUIDv7 (rfc library), DigestSet, JCS (rfc8785), 3 hash types | ~280 |
| `entities.py` | 23 entity models (Work, Person, Edition, EText, Translation, etc.) | ~300 |
| `resolver.py` | Staged resolver R0-R5 (exact → crosswalk → bibliographic → fuzzy → multi-source → scholar) | ~340 |
| `events.py` | Postgres-only canonical event ledger (no JSONL writer) | ~120 |
| `schema_registry.py` | Immutable, versioned schema registry | ~165 |
| `completeness.py` | WorkCompleteness materialized projection | ~170 |
| `ingest.py` | 5-step pipeline (discover→fetch→extract→resolve→store) | ~165 |
| `api.py` | FastAPI v1 (21 endpoints) | ~500 |
| `tests/conformance.py` | 5 binary test suites | ~280 |
| `fingerprint/text.py` | MinHash, shingles, prefix/suffix | ~120 |
| `provenance/derivation.py` | DerivationActivity (PROV-O) | ~60 |
| `provenance/llm_repro.py` | LLM reproducibility tracking | ~60 |
| `signing/checkpoint.py` | Algorithm-tagged signatures | ~80 |
| `anchor/text.py` | TextAnchor with selectors | ~80 |
| `snapshot/manifest.py` | SnapshotManifest | ~60 |
| `reserved.py` | Reserved fields tracking | ~70 |
| `tei_utils.py` | Shared TEI XML parser | ~120 |
| `mcp_server.py` | MCP server for agents | ~80 |

### Adapters (11 active)

| Adapter | Source | Items | Type |
|---|---|---|---|
| GRETIL | TEI XML files | 784 | Local |
| Sanskritree | TypeScript seed | 44 | Local |
| Archive.org | REST API | 8,550 | API |
| Crossref | REST API | 7,677 | API |
| PANDiT | Local JSON | 17,569 | Local |
| OpenAlex | REST API | 96,498 | API |
| Darshana | Local JSON | 2,321 | Local |
| Muktabodha | Zip archives | 499 | Local |
| ORCID | REST API | — | API |
| ROR | REST API | — | API |
| WikiData | SPARQL | — | API |

### Serializers (7)

- PROV-O → prov:Activity/Entity/Agent
- Web Annotation → W3C Annotation JSON-LD
- DataCite → DOI metadata
- CIDOC CRM → crm:E31_Documentary_Object
- RO-Crate → ro-crate-metadata.json
- C2PA → Media provenance manifest
- Hugging Face → Dataset card + export

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

### Evidence Bundle

Machine-produced from actual code execution:
- `data/evidence/evidence-bundle.json`
- `data/runs/e2e-redteam.jsonl` (hermes-verified)
- `data/runs/gates-verified.jsonl` (hermes-verified)

---

## 2. WHAT WAS VERIFIED

### 6 Proofs (all PASS)

| Proof | What it tests | Result |
|---|---|---|
| A: Clean-room bootstrap | 34 tables, all deps, app boots | PASS |
| B: Exact observation | Artifact bytes retained, SHA-256 | PASS |
| C: Identity persistence | Works persist across queries | PASS |
| D: Zero-network replay | 10 events, digests match | PASS |
| E: Epistemic correction | A retracted, B active, history preserved | PASS |
| F: Merge + split | Old IDs resolve, split returns both | PASS |

### 5/5 Conformance Suites

| Suite | What it tests | Result |
|---|---|---|
| CORE | ID uniqueness, UUID format, JCS, schema validity | PASS |
| REPLAY | Event replay, destroy+rebuild | PASS |
| RESOLVER | R0 exact match, false merge prevention | PASS |
| ADAPTER | Structure validation, ExtractionBundle | PASS |
| API | Health, works list, bundle endpoint | PASS |

### End-to-End Red Team (hermes-verified)

| Step | What hermes ran | Result |
|---|---|---|
| Ingest GRETIL | Pipeline ran clean | PASS |
| Query works | 5 works served | PASS |
| Query bundle | 3 assertions in bundle | PASS |
| Conformance | 5/5 PASSED | PASS |

All outputs logged with SHA-256 hashes in `data/runs/e2e-redteam.jsonl`.

---

## 3. DATABASE STATE

```
works:           1,099
assertions:        247
ext_ids:           108
events:          2,181
artifacts:           2
raw_observations:    2
state_cursor:    3,315
state_digest: 6477eadca1de1ab54eb5265e4d1ab929...
```

---

## 4. WHAT'S NOT DONE (from FINAL-TASK.md)

### Phase 1.2 — Self-filling source graph
- DiscoveryObjective generation
- NRAH integration

### Phase 2.0 — Translation availability
- SearchEvent recording
- Negative graph ("searched, none found")

### Phase 2.5+ — Everything after 1.0
See DEV-PLAN.md for full roadmap (17 phases total).

---

## 5. ARCHITECTURE

```
                         PĀṬALA
                           │
         ┌─────────────────┴──────────────────┐
         │                                    │
         ▼                                    ▼
  PERMANENT MEMORY                     ACTIVE INTELLIGENCE
  identity, artifacts,                 agents, models, retrieval,
  observations, assertions,            search, translation,
  provenance, rights,                  argumentation, evolution,
  adjudication, history                planning, media
         │                                    │
         └─────────────────┬──────────────────┘
                           ▼
                 CURRENT QUALIFIED STATE
                           │
                           ▼
                       QUESTIONS
                           │
                           ▼
                PROOF OBLIGATIONS / CRUXES
                           │
              ┌────────────┴────────────┐
              ▼                         ▼
       CHEAP COMPUTATION          SCARCE REALITY
```

---

## 6. FILES (57 Python, 18 Markdown, 22 JSON schemas)

### Core (18 files)
`hashing.py`, `entities.py`, `resolver.py`, `events.py`, `schema_registry.py`,
`completeness.py`, `ingest.py`, `api.py`, `cli.py`, `mcp_server.py`,
`fingerprint/text.py`, `provenance/derivation.py`, `provenance/llm_repro.py`,
`signing/checkpoint.py`, `anchor/text.py`, `snapshot/manifest.py`, `reserved.py`,
`tei_utils.py`

### Adapters (11)
`archiveorg`, `crossref`, `gretil`, `local_json`, `local_seed`, `local_zip`,
`openalex`, `orcid`, `pandit`, `ror`, `wikidata`

### Serializers (7)
`c2pa.py`, `cidoc_crm.py`, `datacite.py`, `huggingface.py`, `prov_o.py`,
`ro_crate.py`, `web_annotation.py`

### Tests
`tests/conformance.py` — 5 binary test suites

### Documentation
`README.md`, `DEV-PLAN.md`, `HANDSOVER-2026-08-17.md`, `FINAL-TASK.md`,
`PEER-REVIEW-2.md`, `PEER-REVIEW-3.md`, `P0-FIX-PLAN.md`,
`NEWBUILDCHECKLIST.md`, `MASTER.md`, `NAVIGATION.md`, `recipes.md`, `agentic.md`,
`docs/api/api-overview.md`, `docs/entities/works.md`, `docs/quickstart.md`,
`docs/rate-limits.md`

---

## 7. GIT STATE

```
Branch: master
Remote: https://github.com/prx0r/wiggly
Commits: 6
Latest: c49d904
```

---

## 8. ANTI-CHEAT RULE

**"Nothing written in README, commit messages or markdown counts as evidence."**

Evidence must be machine-produced from actual code execution.
Evidence bundle at `data/evidence/evidence-bundle.json` is the only valid proof.

---

## 9. WHAT TO DO NEXT

See `DEV-PLAN.md`. Immediate next step is Phase 1.2 (self-filling source graph), not adding more adapters or features.
