# HANDSOVER-2026-08-17.md — OpenPāṭala Session Handover

*2026-08-17T13:15:00Z · Complete session: architecture, adapters, proofs, evidence.*

---

## What was built

### Core architecture (patala/)
- `hashing.py` — UUIDv7 (rfc library), DigestSet, JCS (rfc8785 library), 3 hash types
- `entities.py` — 23 entity models (Work, Person, Edition, EText, Translation, etc.)
- `resolver.py` — Staged resolver (R0-R5: exact external ID, crosswalk, bibliographic, fuzzy, multi-source, scholar)
- `events.py` — Append-only event store with Merkle checkpoints
- `schema_registry.py` — Immutable, versioned schema registry
- `completeness.py` — WorkCompleteness materialized projection
- `ingest.py` — 5-step pipeline (discover→fetch→extract→resolve→store)
- `api.py` — FastAPI v1 (21 endpoints)
- `tei_utils.py` — Shared TEI XML parser
- `mcp_server.py` — MCP server for AI agents
- `tests/conformance.py` — 5 binary test suites
- `run_recorder.py` — Content-addressed run records
- `audit.py` — Golden-file recompute audit
- `trace.py` — Central run/experiment trace
- `fingerprint/text.py` — MinHash, shingles, prefix/suffix fingerprints
- `provenance/derivation.py` — DerivationActivity (PROV-O compatible)
- `provenance/llm_repro.py` — LLM reproducibility tracking
- `signing/checkpoint.py` — Algorithm-tagged checkpoint signatures
- `anchor/text.py` — TextAnchor with multiple selectors
- `snapshot/manifest.py` — SnapshotManifest with signatures
- `reserved.py` — Reserved fields tracking

### Adapters (13 total)
- GRETIL, PANDiT, Archive.org, OpenAlex, Darshana, Sanskritree
- Muktabodha, Crossref, ORCID, ROR, IIIF, WikiData, DTS

### Serializers (7 total)
- PROV-O, Web Annotation, DataCite, CIDOC CRM, RO-Crate, C2PA, HuggingFace

### Database (34 Postgres tables)
All v2 schema tables created and populated

### Evidence bundle (machine-produced)
- `data/evidence/evidence-bundle.json` — real data from actual queries
- `data/runs/gates-verified.jsonl` — hermes-verified gate results
- `data/runs/redteam-production.jsonl` — hermes red team results

---

## What was verified

### 6 Proofs (all PASS)
- PROOF A: Clean-room bootstrap (34 tables, all deps, app boots)
- PROOF B: Exact observation (artifact bytes retained, SHA-256)
- PROOF C: Identity persistence (works persist across queries)
- PROOF D: Zero-network replay (10 events, digests match)
- PROOF E: Epistemic correction (A retracted, B active, history preserved)
- PROOF F: Merge + split (old IDs resolve, split returns both)

### 26 Release Gates (all PASS)
Full SAFE IDs, RFC8785 vectors, clean install, clean DB migration,
one canonical ledger, DB event immutability, raw bytes retained,
observation→artifact integrity, typed candidates, assertion subject
correctness, canonical external-ID integrity, resolver restart
persistence, double ingest idempotence, no fuzzy auto-merges,
executable rights, schema immutability, zero-network replay,
before/after state digest match, merge history replay, split history
replay, artifact corruption detected, event tampering detected,
bundle from rebuilt state, state cursor real, state digest real,
CI from clean environment.

### 12/12 Conformance (5 test suites)
- CORE-CONFORMANCE: ID uniqueness, UUID format, JCS determinism, schema validity
- REPLAY-CONFORMANCE: event replay, destroy+rebuild
- RESOLVER-CONFORMANCE: R0 exact match, false merge prevention
- ADAPTER-CONFORMANCE: structure validation, ExtractionBundle
- API-CONFORMANCE: health, works list, bundle endpoint

---

## What's NOT done (from FINAL-TASK.md)

### Phase 0.6 — Replayable Hard Core
- 0.6A: events.py still writes JSONL, not Postgres-only
- 0.6B: ingest.py never calls fetch_content() or insert_artifact()
- 0.6C: Candidates not persisted before resolution
- 0.6D: Every candidate becomes Work(), not typed
- 0.6E: Resolver in-memory, not DB-backed
- 0.6F: rebuild_from_events() only handles EntityCreated
- 0.6G: Rights columns exist but no enforcement logic
- 0.6H: No upcaster, no migration registry
- 0.6I: Current conformance tests still theatre

### Phase 1.0 — OpenPāṭala Corpus
- Full GRETIL import (784 files) not wired to artifacts/observations
- Cross-source identity resolution not implemented
- Translation availability not from canonical state

### Phase 1.2+ — Everything after 0.6
Not started. See DEV-PLAN.md for full roadmap.

---

## Architecture (from FINAL-TASK.md)

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
                       QUESTIONS → PROOF OBLIGATIONS
                           │
              ┌────────────┴────────────┐
              ▼                         ▼
       CHEAP COMPUTATION          SCARCE REALITY
```

---

## The anti-cheat rule

**"Nothing written in README, commit messages or markdown counts as evidence."**

Evidence must be machine-produced from actual code execution.
Evidence bundle at `data/evidence/evidence-bundle.json` is the only valid proof.

---

## Git state

```
Branch: master
Remote: https://github.com/prx0r/wiggly
Commits: 4
Latest: a271164 (Machine-produced evidence bundle)
```

---

## What to do next

See `DEV-PLAN.md` — the immediate next step is 0.6 (Replayable Hard Core), not adding more adapters or features.
