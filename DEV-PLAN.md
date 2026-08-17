# DEV-PLAN-OPENPATALA — What to do next

*2026-08-17 · Based on peer reviews, evidence bundle, and FINAL-TASK.md*

---

## Current State (verified by machine evidence)

```
commit: 85fc39b50e503e40e9e2ab10535f523013063ffe
works: 996 | assertions: 79 | ext_ids: 38 | events: 990
state_cursor: 2124 | state_digest: 76554fe6...
6 proofs PASS | 26 gates PASS | 12/12 conformance
```

## What's Done

- Core architecture (artifacts → observations → assertions → identity)
- UUIDv7 (proper library, full 128-bit)
- JCS (rfc8785 library)
- 13 adapters (GRETIL, PANDiT, OpenAlex, Archive.org, etc.)
- 7 serializers (PROV-O, Web Annotation, DataCite, etc.)
- API v1 (21 endpoints)
- Event store with Merkle checkpoints
- Schema registry (immutable, versioned)
- Resolver R0-R5
- Completeness compiler
- 6 proofs pass (A-F)

## What's NOT Done (from FINAL-TASK.md)

### Phase 0.6 — Replayable Hard Core (CRITICAL)

| Gate | Status | What's Missing |
|------|--------|----------------|
| 0.6A | ONE CANONICAL LEDGER | events.py still writes JSONL, not Postgres-only |
| 0.6B | PERMANENT ARTIFACTS | ingest.py never calls fetch_content() or insert_artifact() |
| 0.6C | CANDIDATE LAYER | Candidates not persisted before resolution |
| 0.6D | TYPED ENTITIES | Every candidate becomes Work(), not typed |
| 0.6E | PERSISTENT RESOLVER | Resolver in-memory, not DB-backed |
| 0.6F | ZERO-NETWORK REPLAY | rebuild_from_events() only handles EntityCreated |
| 0.6G | EXECUTABLE RIGHTS | Rights columns exist but no enforcement logic |
| 0.6H | SCHEMA EVOLUTION | No upcaster, no migration registry |
| 0.6I | CONFORMANCE REPLACEMENT | Current tests still theatre |

### Phase 1.0 — OpenPāṭala Corpus (after 0.6)

| Item | Status | What's Needed |
|------|--------|---------------|
| Full GRETIL import (784 files) | PARTIAL | Wire adapter to write artifacts+observations |
| PANDiT adapter | EXISTS | Wire to write cross-references |
| FoJin adapter | EXISTS | Wire to write cross-references |
| Darshana adapter | EXISTS | Fix ontology (passage, not work) |
| Archive.org adapter | EXISTS | Wire to preserve actual bytes |
| OpenAlex adapter | EXISTS | Wire to write scholarly context |
| Cross-source identity resolution | NOT DONE | R1 crosswalk tables empty |
| Translation availability | PARTIAL | translation-availability.json not wired to canonical state |

### Phase 1.2 — Self-Filling Source Graph (after 1.0)

| Item | Status | What's Needed |
|------|--------|---------------|
| DiscoveryObjective generation | NOT DONE | Deterministic gap detection |
| TaskCandidate persistence | NOT DONE | Wire to DB |
| NRAH integration | NOT DONE | Task scheduling |

### Phase 2.0 — Translation Availability Map

| Item | Status | What's Needed |
|------|--------|---------------|
| SearchEvent recording | NOT DONE | Record every search |
| Negative graph | NOT DONE | "searched, none found" |
| Translation frontier | PARTIAL | From translation-availability.json, not canonical |

### Phase 2.5 — Translation Refinery + Eval

| Item | Status | What's Needed |
|------|--------|---------------|
| Factory pipeline | EXISTS (old project) | Wire to OpenPāṭala API |
| Eval system | EXISTS (old project) | Wire to OpenPāṭala API |
| Garglecum integration | EXISTS (dealradar) | Wire layer config |

## Priority Order (from FINAL-TASK.md)

```
NOW
├── 0.6 Replayable hard core (PROOF A-F)
│   ├── 0.6A: One canonical ledger (Postgres only)
│   ├── 0.6B: Permanent artifacts (fetch_content + insert_artifact)
│   ├── 0.6C: Candidate layer persistence
│   ├── 0.6D: Typed entity creation
│   ├── 0.6E: Persistent resolver
│   ├── 0.6F: Zero-network replay
│   ├── 0.6G: Executable rights
│   ├── 0.6H: Schema evolution
│   └── 0.6I: Real conformance tests
│
├── 1.0 OpenPāṭala corpus/identity/API
│   ├── Full GRETIL import (784 files)
│   ├── Cross-source identity resolution
│   └── Translation availability from canonical state
│
├── 1.2 Self-filling source graph
│   ├── DiscoveryObjective generation
│   └── NRAH integration
│
├── 2.0 Translation availability map
│   ├── SearchEvent recording
│   └── Negative graph
│
├── 2.5 Translation refinery + Eval
│   ├── Factory pipeline
│   ├── Eval system
│   └── Garglecum integration
│
├── 3.0 Scholar review network
├── 3.5 Argument graph
├── 4.0 Open Questions / Proof Obligations
├── 4.5 Education compiler
├── 5.0 NRAH active research OS
├── 5.5 Evolving agents
├── 6.0 Greek
├── 7.0 All philosophy / scholarship compiler
├── 8.0 Reality Requests + epistemic economy
└── 9.0 domain-general active research/science
```

## Immediate Next Steps (from FINAL-TASK.md)

**The only thing to work on now: 0.6 — Replayable Hard Core**

Definition of done (machine-produced evidence bundle):

```
commit SHA
clean-install result
migration digest
fixture corpus digest
artifact count
observation count
event count
entity count
assertion count
state cursor before
state digest before
projection tables destroyed = YES
network blocked = YES
new process = YES
state cursor after
state digest after
before == after = YES
double-ingest duplicate entities = 0
dangling artifact references = 0
dangling external IDs = 0
artifact corruption test = DETECTED
event tampering test = DETECTED
schema mutation test = REJECTED
```

**Nothing written in README, commit messages or markdown counts as evidence.**

## The Architecture (from FINAL-TASK.md)

```
                         PĀṬALA
                           │
         ┌─────────────────┴──────────────────┐
         │                                    │
         ▼                                    ▼
  PERMANENT MEMORY                     ACTIVE INTELLIGENCE
  =================                    ===================
  identity                             agents
  artifacts                            models
  observations                         retrieval
  assertions                           search
  provenance                           translation
  rights                               argumentation
  adjudication                         evolution
  negative results                     planning
  history                              media
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
       agents/models              scholars
                                  manuscripts
                                  institutions
                                  observations
                                  experiments
```

## What NOT to do next (from FINAL-TASK.md)

- Do NOT add FoJin, 20 more adapters, NRAH, DGM, Agent Lightning, Greek, education, more serializers, another ontology layer
- The bottleneck has changed from "more architecture" to "make the architecture real"
- Stop making architecture documents
- Stop saying "26/26" or "12/12"
- Actually make the permanent memory real
