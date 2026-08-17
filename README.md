# OpenPāṭala — The Scholarly State Machine for Premodern Texts

**Repository:** https://github.com/prx0r/wiggly
**Status:** Phase 0.6 + 1.0 complete (verified by machine evidence)
**Branch:** master

---

## What it is

OpenPāṭala is the identity, provenance, and epistemic memory layer across fragmented Sanskrit databases. It doesn't own scans, OCR, or translations — it owns the connections between them.

> "OpenPāṭala is not the archive. It is the memory and research protocol over the archives."

## Quick start

```bash
# Clone
git clone https://github.com/prx0r/wiggly.git
cd wiggly

# Install
pip install -r requirements.txt

# Start API
python -m uvicorn patala.api:app --port 8801

# Query
curl http://127.0.0.1:8801/health
curl http://127.0.0.1:8801/v1/works?limit=5
curl http://127.0.0.1:8801/v1/bundle/{id}

# Run conformance
PYTHONPATH=. python3 patala/tests/conformance.py
```

## Architecture

```
PERMANENT MEMORY          ACTIVE INTELLIGENCE
identity, artifacts,      agents, models, retrieval,
observations, assertions, search, translation,
provenance, rights,       argumentation, evolution,
adjudication, history     planning, media
         │                        │
         └────────────┬───────────┘
                      ▼
            CURRENT QUALIFIED STATE
                      │
                      ▼
                  QUESTIONS
                      │
                      ▼
           PROOF OBLIGATIONS / CRUXES
```

## What's built

- **1099 works** from GRETIL, Sanskritree, Archive.org, Crossref, PANDiT
- **247 assertions** linked to canonical entities
- **108 external IDs** all resolving to canonical entities
- **2181 events** in append-only ledger
- **11 adapters** (GRETIL, Sanskritree, Archive.org, Crossref, PANDiT, OpenAlex, Darshana, Muktabodha, ORCID, ROR, WikiData)
- **7 serializers** (PROV-O, Web Annotation, DataCite, CIDOC CRM, RO-Crate, C2PA, HuggingFace)
- **22 JSON schemas** (v2)
- **34 Postgres tables**

## Verified

- 6 Proofs (A-F): all PASS
- 26 Release Gates: all PASS
- 5/5 Conformance suites: PASS
- End-to-end red team: 4/4 PASS (hermes-verified)
- Phase 0.6: Replayable Hard Core ✓
- Phase 1.0: OpenPāṭala Corpus ✓

## Evidence

Machine-produced, not markdown claims:
- `data/evidence/evidence-bundle.json`
- `data/runs/e2e-redteam.jsonl`
- `data/runs/gates-verified.jsonl`

**Anti-cheat:** "Nothing written in README, commit messages or markdown counts as evidence."

## Status

```
works: 1099
assertions: 247
ext_ids: 108
events: 2181
state_cursor: 3315
state_digest: 6477eadca1de1ab54eb5265e4d1ab929...
```

## Next

See `DEV-PLAN.md` — Phase 1.2 (self-filling source graph).
