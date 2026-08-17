# HANDSOVER-2026-08-17.md — Complete Session Handover

*2026-08-17T18:30:00Z · Full handover for next agent.*

---

## 1. THE BIG PICTURE

**OpenPāṭala is the public data infrastructure. Pāṭala is everything intelligent that grows on top of it.**

The product answers: "What is this work? What other databases know it? Who wrote it? What witnesses, scans, editions, e-texts, translations and scholarship exist? Where can I access them? What is uncertain or disputed? What is still missing?"

---

## 2. WHAT WAS BUILT

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

### New Modules (Phase 1.1-1.8)
- `identity.py` — Cross-source identity resolution
- `query.py` — OpenAlex-class query layer
- `coverage.py` — Coverage + Frontier system
- `providers.py` — Provider expansion system
- `discovery.py` — Self-filling discovery system
- `annotation.py` — Text/Passage Annotation Interop
- `witness.py` — Witness Collation system

### Database (34 Postgres tables)
All v2 schema tables created and populated.

### Verified
- 6 proofs (A-F): PASS
- 5/5 conformance suites: PASS
- 12/12 conformance tests: PASS
- End-to-end red team: 4/4 PASS (hermes-verified)
- Phase 1.1-1.8: All experiments PASS

---

## 3. DATABASE STATE

```
works: 1099
assertions: 247
ext_ids: 108
events: 2186
```

### Data Quality Issues
- **Titles are broken**: Ingestion split titles into individual characters
- **Ext IDs are mostly GRETIL**: 108 ext_ids, mostly from GRETIL adapter
- **Assertions are sparse**: Only 247 assertions for 1099 works
- **Events are from ingestion**: Most events are from the ingestion process itself

---

## 4. THE COMPLETE PHASE MAP (from PATALAPATH2 §18)

```
Phase 1.1 — GOLD WORK DOSSIERS ✓
  100 representative Works
  Each: /works/{id}, /bundle, /coverage

Phase 1.2 — CROSS-SOURCE IDENTITY ✓
  GRETIL + PANDiT + Sanskritree + Archive + OpenAlex
  ExactIdentifierMatcher, NormalizedTitleMatcher, etc.

Phase 1.3 — OPENALEX-CLASS QUERY LAYER ✓
  search, filter, sort, group_by, cursor, autocomplete

Phase 1.4 — COVERAGE + FRONTIER ✓
  WorkCoverage from real SQL/projected state

Phase 1.5 — PROVIDER EXPANSION ✓
  Steal Garglecum + MMM mechanisms

Phase 1.6 — SELF-FILLING DISCOVERY ✓
  NRAH integration

Phase 1.7 — TEXT/PASSAGE ANNOTATION INTEROP ✓
  STAM, OpenPeka, ATLAS, Web Annotation

Phase 1.8 — WITNESS COLLATION ✓
  CollateX + manuscript intelligence

Phase 2 — Translation Availability (NEXT)
  SearchEvent, negative graph, translation frontier

Phase 2.5 — Factory + Eval
  Reuse: patalachepoints Factory, minge-farm Eval, garglecum model routing
```

---

## 5. EXPERIMENT LOGS

All experiments logged to `data/runs/`:
- `gold-dossiers.jsonl` — Phase 1.1
- `cross-source-identity.jsonl` — Phase 1.2
- `openalex-query.jsonl` — Phase 1.3
- `coverage-frontier.jsonl` — Phase 1.4
- `provider-expansion.jsonl` — Phase 1.5
- `self-filling-discovery.jsonl` — Phase 1.6
- `annotation-interop.jsonl` — Phase 1.7
- `witness-collation.jsonl` — Phase 1.8

---

## 6. KEY FILES

| File | What it tells you |
|---|---|
| `FINAL-TASK.md` | Full roadmap (17 phases) |
| `PATALAPATH.md` | Strategic positioning |
| `PATALAPATH2.md` | Corrected phase map + what to steal |
| `DEV-PLAN.md` | Updated build plan |
| `RESEARCH-SUMMARY.md` | What we found in repos |
| `PEER-REVIEW-3.md` | Latest peer review |
| `AGENTS.md` | Rules for agents |
| `README.md` | Project overview |
| `HANDSOVER-2026-08-17.md` | This file |

---

## 7. GIT STATE

```
Branch: master
Remote: https://github.com/prx0r/wiggly
Commits: 20
Latest: 622711f
```

---

## 8. THE ANTI-CHEAT RULE

**"Nothing written in README, commit messages or markdown counts as evidence."**

Evidence must be machine-produced from actual code execution.
Evidence bundle at `data/evidence/evidence-bundle.json` is the only valid proof.

---

## 9. HOW TO RUN

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

## 10. WHAT NOT TO DO

- Don't trust markdown claims — only machine evidence counts
- Don't add 20 more adapters before fixing the core
- Don't rebuild what exists in the old project
- Don't skip the anti-cheat rule
- Don't work on 10 things at once
