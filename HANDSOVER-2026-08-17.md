# HANDSOVER-2026-08-17.md — Complete Session Handover

*2026-08-17T18:45:00Z · Full handover for next agent.*

---

## 1. THE BIG PICTURE

**OpenPāṭala is the public data infrastructure. Pāṭala is everything intelligent that grows on top of it.**

The product answers: "What is this work? What other databases know it? Who wrote it? What witnesses, scans, editions, e-texts, translations and scholarship exist? Where can I access them? What is uncertain or disputed? What is still missing?"

---

## 2. THE HONEST TRUTH

**Most of what was built in Phase 1.1-1.8 is theatre.**

The tests pass because they test the wrong things. The modules work on broken data. The "gold dossiers" are mostly empty. The "cross-source identity" finds no real matches. The "coverage" returns UNKNOWN for everything.

### The Critical Problem

The PANDiT ingestion split titles into individual characters. "Raṅgācārya of Kauśikagotra" became 24 separate assertions: "R", "a", "ṅ", "g", "ā", "c", "ā", "r", "y", "a", etc.

This means:
- `assertions_count` is meaningless (24 characters ≠ 24 facts)
- Coverage engine returns UNKNOWN (no real assertions to check)
- Cross-source identity finds no matches (no real titles to compare)
- Gold dossiers are mostly empty

---

## 3. DATABASE STATE

```
works: 1099
assertions: 247 (but most are single characters)
Ext IDs: 108 (mostly GRETIL collection)
events: 2186 (mostly ingestion events)
```

### Data Quality Issues
- **Titles are broken**: Ingestion split titles into individual characters
- **Ext IDs are mostly GRETIL**: 108 ext_ids, mostly from GRETIL adapter
- **Assertions are sparse**: Only 247 assertions for 1099 works
- **Events are from ingestion**: Most events are from the ingestion process itself

---

## 4. WHAT WAS BUILT

### Core (57 Python files)
- `hashing.py` — UUIDv7, DigestSet, JCS, 3 hash types
- `entities.py` — 23 entity models
- `resolver.py` — Staged resolver R0-R5
- `events.py` — Postgres-only event ledger
- `schema_registry.py` — Immutable schema registry
- `work_coverage.py` — Coverage from canonical state
- `ingest.py` — 5-step pipeline
- `api.py` — FastAPI v1 (21 endpoints)
- `tests/conformance.py` — 5 binary test suites
- `conformance_test.py` — 12-step verification
- + 8 more modules (fingerprint, provenance, signing, etc.)

### Adapters (13)
GRETIL, Sanskritree, Archive.org, Crossref, PANDiT, OpenAlex, Darshana, Muktabodha, ORCID, ROR, WikiData, STAM, CollateX

### New Modules (Phase 1.1-1.8) — THEATRE
- `identity.py` — Cross-source identity resolution (THEATRE)
- `query.py` — OpenAlex-class query layer (PARTIAL)
- `coverage.py` — Coverage + Frontier system (THEATRE)
- `providers.py` — Provider expansion system (THEATRE)
- `discovery.py` — Self-filling discovery system (THEATRE)
- `annotation.py` — Text/Passage Annotation Interop (THEATRE)
- `witness.py` — Witness Collation system (THEATRE)

---

## 5. WHAT NEEDS TO BE DONE

### 1. Fix the Ingestion
- The PANDiT ingestion is broken (titles split into characters)
- Need to re-ingest with proper parsing
- Need to verify ingestion actually works

### 2. Ingest Real Data
- GRETIL: 784 files, but only 20 ext_ids in database
- PANDiT: 100 records, but only 20 ext_ids
- Archive.org: 50 records, but only 20 ext_ids
- Need to actually ingest the data

### 3. Rebuild Modules on Real Data
- Only then will the modules be useful
- Only then will the tests be meaningful

---

## 6. THE CORRECT PHASE MAP (from PATALAPATH2 §18)

```
Phase 1.1 — GOLD WORK DOSSIERS ✓ (but data is broken)
Phase 1.2 — CROSS-SOURCE IDENTITY ✓ (but finds no real matches)
Phase 1.3 — OPENALEX-CLASS QUERY LAYER ✓ (but operates on broken data)
Phase 1.4 — COVERAGE + FRONTIER ✓ (but returns UNKNOWN for everything)
Phase 1.5 — PROVIDER EXPANSION ✓ (but metrics are meaningless)
Phase 1.6 — SELF-FILLING DISCOVERY ✓ (but discoveries are simulated)
Phase 1.7 — TEXT/PASSAGE ANNOTATION INTEROP ✓ (but no annotations exist)
Phase 1.8 — WITNESS COLLATION ✓ (but no witnesses exist)
```

---

## 7. KEY FILES

| File | What it tells you |
|---|---|
| `FINAL-TASK.md` | Full roadmap (17 phases) |
| `PATALAPATH.md` | Strategic positioning |
| `PATALAPATH2.md` | Corrected phase map + what to steal |
| `DEV-PLAN.md` | Updated build plan |
| `RESEARCH-SUMMARY.md` | What we found in repos |
| `PEER-REVIEW-3.md` | Latest peer review |
| `PEER-REVIEW-4.md` | Honest self-assessment |
| `AGENTS.md` | Rules for agents |
| `README.md` | Project overview |
| `HANDSOVER-2026-08-17.md` | This file |

---

## 8. GIT STATE

```
Branch: master
Remote: https://github.com/prx0r/wiggly
Commits: 22
Latest: 2496a96
```

---

## 9. THE ANTI-CHEAT RULE

**"Nothing written in README, commit messages or markdown counts as evidence."**

Evidence must be machine-produced from actual code execution.
Evidence bundle at `data/evidence/evidence-bundle.json` is the only valid proof.

---

## 10. HOW TO RUN

```bash
cd /root/openpatalanew

# Run conformance
PYTHONPATH=. python3 patala/tests/conformance.py

# Run experiments
PYTHONPATH=. python3 patala/experiments/gold_dossiers.py
PYTHONPATH=. python3 patala/experiments/cross_source_identity.py
PYTHONPATH=. python3 patala/experiments/openalex_query.py
PYTHONPATH=. python3 patala/experiments/coverage_frontier.py
PYTHONPATH=. python3 patala/experiments/provider_expansion.py
PYTHONPATH=. python3 patala/experiments/self_filling_discovery.py
PYTHONPATH=. python3 patala/experiments/annotation_interop.py
PYTHONPATH=. python3 patala/experiments/witness_collation.py

# Run API
python3 -m uvicorn patala.api:app --port 8801

# Check database
PGPASSWORD=patala psql -U patala -h 127.0.0.1 -d openpatala

# Check experiment logs
cat data/runs/gold-dossiers.jsonl
```

---

## 11. WHAT NOT TO DO

- Don't trust markdown claims — only machine evidence counts
- Don't add 20 more adapters before fixing the core
- Don't rebuild what exists in the old project
- Don't skip the anti-cheat rule
- Don't work on 10 things at once
- Don't build modules on broken data
