# OpenPāṭala — The Scholarly State Machine for Premodern Texts

*From-scratch rebuild per newbuildmainspec. Production-grade. Postgres-backed.*

---

## What it does

For any Sanskrit work, discover: the canonical work, known alternative titles, authorship uncertainty, editions, available texts, translations, manuscripts, scholarship and provenance.

**That's it. Not millions of records. Not a perfect ontology. Just: name → everything known about it.**

## Quick start

```bash
cd /root/openpatalanew
pip install -r requirements.txt

# Start API
python3 -m uvicorn patala.api:app --port 8801

# Query
curl http://127.0.0.1:8801/health
curl http://127.0.0.1:8801/v1/works?limit=5
curl http://127.0.0.1:8801/v1/bundle/{id}

# Test
python3 patala/conformance_test.py
```

## Documentation

| Doc | What |
|---|---|
| [README.md](README.md) | This file |
| [docs/quickstart.md](docs/quickstart.md) | 5-minute tutorial |
| [docs/api/api-overview.md](docs/api/api-overview.md) | API reference |
| [docs/entities/works.md](docs/entities/works.md) | Work entity docs |
| [docs/rate-limits.md](docs/rate-limits.md) | Rate limits and auth |
| [recipes.md](recipes.md) | Copy-paste how-tos (R1-R8) |
| [agentic.md](agentic.md) | Hermes runbook |
| [MASTER.md](MASTER.md) | Project index |
| [NAVIGATION.md](NAVIGATION.md) | Quick reference |
| [BUILD-NOTES-2026-08-17.md](BUILD-NOTES-2026-08-17.md) | Timestamped build log |
| [HANDSOVER-2026-08-17.md](HANDSOVER-2026-08-17.md) | Session handover |
| [NEWBUILDCHECKLIST.md](NEWBUILDCHECKLIST.md) | Implementation verification |

## Architecture

```
LAYER 0 — ARTIFACTS:        exact observed bytes
LAYER 1 — OBSERVATIONS:     who/where/when those bytes came from
LAYER 2 — EXTRACTIONS:      what parsers/models extracted
LAYER 3 — ASSERTIONS:       what sources/actors claim
LAYER 4 — IDENTITY:         what entities those claims refer to
LAYER 5 — ADJUDICATION:     what has been reviewed/accepted/rejected
LAYER 6 — CURRENT STATE:    materialized scholarly view (rebuildable)
LAYER 7 — PRODUCTS:         API/search/Factory (can disappear entirely)
```

## System status

```
PostgreSQL: 613 works, 77 assertions, 38 ext_ids, 613 events
Tables: 34
Adapters: 13 (GRETIL, PANDiT, Archive.org, OpenAlex, Darshana, Sanskritree,
         Muktabodha, Crossref, ORCID, ROR, IIIF, WikiData, DTS)
Serializers: 7 (PROV-O, Web Annotation, DataCite, CIDOC CRM, RO-Crate, C2PA, HuggingFace)
API: 18 endpoints
Conformance: 12/12 PASS
Hermes: mimo-v2.5, real calls, runs logged
```

## 12 Architectural Invariants

1. Entity identity is opaque and independent of content
2. Original observations are never silently rewritten
3. Every permanently stored record identifies the exact schema
4. Published schemas are immutable
5. Breaking semantic changes create new schemas
6. Current database tables are rebuildable projections
7. Every derivation resolves to exact inputs
8. Hash algorithms explicitly tagged and replaceable
9. Fixity does not imply truth
10. Merged/split/retired IDs permanently resolvable
11. Rights never silently broadened
12. Artifacts + events + schemas → rebuildable state
