# DEV-PLAN.md — Updated Build Plan

*2026-08-17T16:30:00Z · Updated after research: 7 repos cloned, pathway analyzed*

---

## Current State

```
Phase 0.6: Replayable Hard Core ✓
Phase 1.0: OpenPāṭala Corpus ✓
  1099 works, 247 assertions, 108 ext_ids, 2181 events
  11 adapters, 7 serializers, 22 schemas, 34 tables
  5/5 conformance PASS, 12/12 conformance PASS
```

## What Changed (from research)

### Stealable (directly usable)

| Repo | What to steal | How it maps to Pāṭala |
|---|---|---|
| STAM | Annotation model (text spans + higher-order annotations) | TextAnchor → STAM annotation → STAM store |
| CollateX | Witness alignment + variant graphs | GRETIL text + manuscript → CollateX → Edition apparatus |
| OpenPecha | Base text + stand-off annotation separation | Artifact = base text, Annotation = stand-off layers |

### Study (pattern extraction)

| Repo | What to study | How it maps |
|---|---|---|
| MMM | TEI → CIDOC-CRM → RDF pipeline | TEI → RawObservation → CandidateAssertion → Entity |
| Perseus/Scaife | ATLAS annotation integration | Pāṭala passages → ATLAS annotations → EvidenceUse |
| Pairwise-light | Text-reuse analysis | DERIVED_FROM edges between passages |

## Updated Build Order

### Phase 0.6 — Replayable Hard Core ✓ (DONE)
- 0.6A: Postgres-only ledger ✓
- 0.6B: Permanent artifacts ✓
- 0.6C: Candidate persistence ✓
- 0.6D: Typed entity creation ✓
- 0.6E: Persistent resolver ✓
- 0.6F: Zero-network replay ✓
- 0.6G: Executable rights ✓
- 0.6H: Schema evolution ✓
- 0.6I: Real conformance tests ✓

### Phase 1.0 — OpenPāṭala Corpus ✓ (DONE)
- Full GRETIL import: 784 files, 1995 assertions
- Sanskritree import: 44 works, 88 assertions
- Archive.org: 20 items ingested
- Crossref: 20 items ingested
- PANDiT: 20 items ingested
- Total: 1099 works, 247 assertions, 108 ext_ids

### Phase 1.1 — Integrate Stealable Repos (NEW)
- [ ] STAM integration: TextAnchor → STAM annotation adapter
- [ ] CollateX integration: witness alignment for editions
- [ ] OpenPecha pattern: base text + annotation separation
- [ ] MMM pattern: TEI → RawObservation → CandidateAssertion

### Phase 1.2 — Self-Filling Source Graph
- [ ] DiscoveryObjective generation (deterministic gap detection)
- [ ] NRAH task scheduling
- [ ] TaskCandidate persistence

### Phase 1.3 — Cross-Source Identity Resolution
- [ ] PANDiT ↔ GRETIL ↔ OpenAlex crosswalk tables
- [ ] R1 deterministic crosswalk implementation
- [ ] Text fingerprinting for deduplication

### Phase 2.0 — Translation Availability Map
- [ ] SearchEvent recording (every search logged)
- [ ] Negative graph ("searched, none found")
- [ ] Translation frontier from canonical state

### Phase 2.5 — Translation Refinery + Eval
- [ ] Factory pipeline (from autotranslate.md)
- [ ] RAW SANSKRIT → L0 (the missing piece)
- [ ] Eval system
- [ ] Garglecum layer config integration

### Phase 3.0 — Scholar Review Network
- [ ] Scholar profiles
- [ ] Attestation system
- [ ] Calibration tracking

### Phase 3.5 — Argument Graph
- [ ] Proposition/Inference/Argument models
- [ ] Support/Attack/Defeater edges
- [ ] Crux identification

### Phase 4.0 — Open Questions / Proof Obligations
- [ ] OpenQuestion model
- [ ] Hypothesis tracking
- [ ] EpistemicCeiling detection

### Phase 4.5 — Education Compiler
- [ ] Learning objectives from arguments
- [ ] Proof-carrying education
- [ ] Misconception tracking

### Phase 5.0 — NRAH Active Research OS
- [ ] Objective/Milestone/Task models
- [ ] Budget/Resource tracking
- [ ] Agent orchestration

### Phase 5.5 — Evolving Agents
- [ ] SystemIssue tracking
- [ ] AgentVariant management
- [ ] ADIAS/ADAS/DGM evolution

### Phase 6.0 — Greek
- [ ] Perseus/OpenGreekAndLatin adapter
- [ ] CTS/URIs integration
- [ ] Cross-tradition identity resolution

### Phase 7.0 — All Philosophy
- [ ] Latin/Arabic/Tibetan/Pāli/Chinese adapters
- [ ] Cross-tradition comparison
- [ ] Scholarly network

### Phase 8.0 — Reality Requests + Epistemic Economy
- [ ] EpistemicCeiling detection
- [ ] RealityRequest generation
- [ ] Funding allocation

### Phase 9.0 — Domain-General Active Research
- [ ] Science integration
- [ ] Sensor/field observation
- [ ] Experimental design

## Priority: Phase 1.1 (Integrate Stealable Repos)

This is the immediate next step. The repos are already cloned:
- `research/stam/` — annotation model
- `research/collatex/` — witness alignment
- `research/toolkit-v2/` — OpenPecha text+annotation separation
- `research/mmm-data-conversion/` — TEI ingestion pattern
- `research/explorehomer-atlas/` — ATLAS annotation pattern

Integration plan:
1. Study STAM API → build TextAnchor adapter
2. Study CollateX API → build witness alignment module
3. Study OpenPecha pattern → separate base text from annotations
4. Study MMM pattern → build TEI → RawObservation transformation
