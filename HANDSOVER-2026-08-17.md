# HANDSOVER-2026-08-17.md — Complete Session Handover

*2026-08-17T17:15:00Z · Full handover for next agent.*

---

## 1. THE BIG PICTURE

**OpenPāṭala is the public data infrastructure. Pāṭala is everything intelligent that grows on top of it.**

```
                    OPENPĀṬALA
        canonical reality/data infrastructure
                         │
       ┌─────────────────┼──────────────────┐
       │                 │                  │
       ▼                 ▼                  ▼
   FACTORY             SCHOLAR          EDUCATION
 translation         research OS       proof learning
 evaluation          arguments
 commentary          questions
```

**The product:** "What is this work? What other databases know it? Who wrote it? What witnesses, scans, editions, e-texts, translations and scholarship exist? Where can I access them? What is uncertain or disputed? What is still missing?"

---

## 2. WHAT WAS BUILT

### Core (57 Python files)

| Module | Purpose |
|---|---|
| `hashing.py` | UUIDv7, DigestSet, JCS, 3 hash types |
| `entities.py` | 23 entity models |
| `resolver.py` | Staged resolver R0-R5 |
| `events.py` | Postgres-only event ledger |
| `schema_registry.py` | Immutable schema registry |
| `work_coverage.py` | Coverage from canonical state |
| `ingest.py` | 5-step pipeline |
| `api.py` | FastAPI v1 (21 endpoints) |
| `tests/conformance.py` | 5 binary test suites |
| + 8 more modules | fingerprint, provenance, signing, etc. |

### Adapters (11)
GRETIL, Sanskritree, Archive.org, Crossref, PANDiT, OpenAlex, Darshana, Muktabodha, ORCID, ROR, WikiData

### Database (34 Postgres tables)
All v2 schema tables created and populated.

### Research (7 repos cloned)
STAM, CollateX, OpenPecha, MMM, bibma-metadata, pairwise-light, explorehomer-atlas

### Verified
- 6 proofs (A-F): PASS
- 5/5 conformance suites: PASS
- 12/12 conformance tests: PASS
- End-to-end red team: 4/4 PASS (hermes-verified)

---

## 3. DATABASE STATE

```
works: 1099
assertions: 247
ext_ids: 108
events: 2181
```

---

## 4. ADVICE FOR NEXT AGENT

### How to stay organized

1. **Read AGENTS.md first** — it has the rules
2. **Read DEV-PLAN.md** — it has the build order
3. **Read FINAL-TASK.md** — it has the full roadmap
4. **Never trust README claims** — only machine-produced evidence counts
5. **One change = one commit** — don't batch unrelated changes
6. **Test before claiming done** — run conformance, not just unit tests

### How to be efficient

1. **Don't rebuild what exists** — check the old project (`/root/openpatalaproject/`) first
2. **Don't add features before fixing architecture** — Phase 0.6 before Phase 1.0
3. **Don't trust markdown** — only evidence from `data/evidence/` counts
4. **Don't skip the anti-cheat rule** — "Nothing written in README counts as evidence"
5. **Don't work on 10 things at once** — pick one phase, complete it, verify, commit

### The build discipline

1. **Read the spec** — understand what's required
2. **Check what exists** — don't rebuild the wheel
3. **Implement the minimum** — don't overbuild
4. **Test with real data** — not unit tests on mocks
5. **Log everything** — hermes runs, content-addressed records
6. **Verify before claiming done** — conformance tests, not "it works on my machine"
7. **Commit with evidence** — machine-produced, not markdown claims

### What NOT to do

- Don't add 20 more adapters before fixing the architecture
- Don't write another 1,500-line architecture document
- Don't say "26/26" or "12/12" without real verification
- Don't rebuild things that already exist in the old project
- Don't skip the anti-cheat rule

### The priority order

```
NOW: Phase 1.1 (Integrate Stealable Repos)
├── STAM → TextAnchor adapter
├── CollateX → witness alignment
├── OpenPecha → base text + annotation separation
└── MMM → TEI ingestion pattern

THEN: Phase 1.2 (Self-Filling Source Graph)
THEN: Phase 1.3 (Cross-Source Identity Resolution)
THEN: Phase 2.0 (Translation Availability)
```

---

## 5. KEY FILES

| File | What it tells you |
|---|---|
| `FINAL-TASK.md` | Full roadmap (17 phases) |
| `PATHWAY.md` | Strategic positioning |
| `PATALAPATH.md` | Same as PATHWAY.md |
| `DEV-PLAN.md` | Updated build plan |
| `RESEARCH-SUMMARY.md` | What we found in repos |
| `PEER-REVIEW-3.md` | Latest peer review |
| `AGENTS.md` | Rules for agents |
| `README.md` | Project overview |

---

## 6. GIT STATE

```
Branch: master
Remote: https://github.com/prx0r/wiggly
Commits: 10
Latest: a01c9ea
```

---

## 7. THE ONE RULE

> **Nothing is "real" because a file exists. It is real when an independently defined task,
> human-grounded gold, and a reproducible, LOGGED gate show it does what its name claims.**

---

## 8. THE ANTI-CHEAT RULE

**"Nothing written in README, commit messages or markdown counts as evidence."**

Evidence must be machine-produced from actual code execution.
Evidence bundle at `data/evidence/evidence-bundle.json` is the only valid proof.
