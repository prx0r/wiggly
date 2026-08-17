Yes. Strip everything back to **five near-term checkpoints**. You already have most of the scaffolding; the next job is to turn specific layers from “containers/proposals” into **validated scholarly capabilities**.

The sequence I would freeze is:

```text
CP0  BENCHMARK REAL
        ↓
CP1  PHILOLOGICAL PROOF REAL
        ↓
CP2  EVIDENCE RETRIEVAL REAL
        ↓
CP3  THEMES REAL
        ↓
CP4  ARGUMENTS REAL
        ↓
      [then semantic verification → adversarial review → essays]
```

Everything the two agents do should advance one of those five.

---

# 1. CP0 — Pāṭala Benchmark Suite v0 becomes genuinely real

### Where you are

Very close structurally.

You have:

* benchmark framework;
* task families;
* `ARG-GOLD-001`;
* leakage thinking;
* existing retrieval fixtures;
* reproducible machinery.

But the **gold population is still thin**.

### What completion means

Not “benchmark directory exists.”

It means you have a small set of genuinely human-checked evaluation objects:

```text
PATALA-RETRIEVAL
~40–50 reviewed queries

PATALA-EVIDENCE
~20–30 claim ↔ evidence judgments

PATALA-STRUCTURE
5–10 real hand-reconstructed arguments

PATALA-FIDELITY
~20–30 transformations + adversarial corruptions
```

Don't chase hundreds yet.

### The important data structure

Implement/freeze one universal:

```ts
interface BenchmarkFixture {
  fixture_id: string;
  benchmark_version: string;

  task:
    | "PASSAGE_RETRIEVAL"
    | "TERM_RETRIEVAL"
    | "CLAIM_SUPPORT"
    | "COUNTEREVIDENCE"
    | "ARGUMENT_EXTRACTION"
    | "FIDELITY";

  inputs: Ref[];
  expected: unknown;

  provenance: Ref[];

  review_state:
    | "CANDIDATE"
    | "SINGLE_REVIEWED"
    | "DOUBLE_REVIEWED"
    | "ADJUDICATED";

  split:
    | "DEV"
    | "EVAL_ONLY"
    | "ARGUMENT_FAMILY_HELD_OUT"
    | "WORK_HELD_OUT";

  allowed_training_use: boolean;
}
```

And:

```ts
interface BenchmarkRun {
  run_id: string;
  benchmark_version: string;
  git_commit: string;
  model_or_method: string;
  config_hash: string;

  predictions: Ref;
  metrics: Record<string, number>;
  error_analysis: Ref;
}
```

### Gate

From this checkpoint onward:

> No model “works” unless there is a `BenchmarkRun` demonstrating it.

That single rule stops most of the theater.

---

# 2. CP1 — PhilologicalProof v1

### Where you are

This is actually the **closest major checkpoint**.

V2/V3 now has:

```text
35/35 P0 PASS
0 unknown source chars
exact spans
complete classification
```

And P2 Vidyut witnesses already exist across ~104k records.

That's real.

### What remains

Don't make CP1 mean “machine proves translation correctness.”

Make CP1:

> **Every material source→L0 translation decision can expose what is mechanically proven, linguistically supported, unresolved, or editor-dependent.**

Finish in this order:

```text
P0 exact source coverage       ✅

P1 segmentation/sandhi
Vidyut

P2 morphology
Vidyut + Heritage ensemble

P3 lexical sense
gold fixtures → ranker benchmark

P4 alignment
gold alignment → baseline/model benchmark

P5 syntax/referents
later / selective high-risk cases
```

### Most important structure to freeze NOW

```ts
interface PhilologicalProof {
  proof_id: string;

  passage_id: PassageId;
  source_span_ids: SourceSpanId[];

  source_integrity: ProofDimension;
  extraction_coverage: ProofDimension;
  segmentation: ProofDimension;
  morphology: ProofDimension;
  syntax: ProofDimension;
  alignment: ProofDimension;
  lexical_sense: ProofDimension;

  open_issues: PhilologicalIssue[];

  tool_witnesses: ToolWitness[];
  review_events: ReviewEventId[];
}
```

Where:

```ts
interface ProofDimension {
  status:
    | "PROVED"       // deterministic
    | "SUPPORTED"    // external/tool evidence
    | "CONFLICT"
    | "OPEN"
    | "UNCHECKED"
    | "REVIEWED";    // actual human review only

  evidence_ids: string[];
}
```

Do **not** invent `confidence: .93`.

### Why this matters to the vision

This immediately becomes:

```text
/verify-translation
```

And eventually:

> “Upload your Sanskrit translation and Pāṭala shows exactly where philological judgment enters.”

That is already a scholar product.

---

# 3. CP2 — Evidence retrieval becomes trustworthy

This should come **before more clever graph ML**.

### Where you are

You already have:

* passages;
* C1;
* terms;
* translation decisions;
* relations;
* evidence roles;
* resolve kernel.

But retrieval quality has not yet become a properly benchmarked capability.

### Build

Run against CP0:

```text
BM25
vs
dense
vs
hybrid
vs
late interaction later
```

For questions like:

```text
find passages supporting X

find uses of vimarśa in this function

find passages relevant to order-less support

find passages challenging claim C
```

### Data structures needed now

Don't make search results strings.

Make them scholarly candidates:

```ts
interface EvidenceCandidate {
  candidate_id: string;

  query_id?: string;
  target_claim_id?: string;

  passage_id: PassageId;
  source_span_ids?: SourceSpanId[];

  relation:
    | "SUPPORT_CANDIDATE"
    | "CONTRADICT_CANDIDATE"
    | "QUALIFY_CANDIDATE"
    | "PARALLEL_CANDIDATE"
    | "UNKNOWN";

  retrieval_method: string;
  retrieval_score?: number;

  status: "MACHINE_PROPOSED" | "REVIEWED" | "ACCEPTED" | "REJECTED";
}
```

Retrieval score is explicitly:

> relevance-ranking score

not:

> truth score.

### Gate

Production method has to beat the trivial baseline on frozen retrieval fixtures.

### Vision unlocked

This creates the first serious version of **Explore**:

> “Show me the evidence space around this idea.”

And enables nearly everything later:

* counterevidence;
* adversarial translation review;
* thesis stress tests;
* theme discovery;
* peer review.

---

# 4. CP3 — Themes become real scholarly objects

### Where you are

You have:

```text
9 graph/community proposals
+
themes.ts lemma/topic system
```

but no unified editorial Theme layer.

So this is close.

### Do not build another clustering algorithm

Unify the representation first.

You need:

```ts
interface Theme {
  theme_id: string;

  title: string;
  question: string;

  state:
    | "MACHINE_PROPOSED"
    | "EDITOR_REVIEWED"
    | "ACCEPTED"
    | "REJECTED"
    | "SUPERSEDED";

  memberships: ThemeMembership[];

  recurring_claims: string[];
  tensions: string[];
  important_terms: ConceptId[];

  boundary: {
    includes: string[];
    does_not_claim: string[];
  };

  proposal_provenance?: {
    clustering_run_id: string;
    algorithm: string;
  };

  review_events: ReviewEventId[];
}
```

And:

```ts
interface ThemeMembership {
  c1_id: C1Id;

  role:
    | "DEFINES"
    | "ESTABLISHES"
    | "DEVELOPS"
    | "APPLIES"
    | "QUALIFIES"
    | "CONTRASTS";

  strength:
    | "CORE"
    | "SUPPORTING"
    | "CONTRAST"
    | "TANGENTIAL";

  evidence_ids: string[];
}
```

### Immediate target

Don't adjudicate everything.

Take perhaps **3 of the 9 proposals**:

```text
Order-less Support
Vimarśa
Pramāṇa
```

and genuinely adjudicate them.

Then you finally have:

```text
AcceptedTheme
```

objects.

### Gate

A theme isn't accepted because clustering found it.

It is accepted because someone inspected:

* its members;
* exclusions;
* boundary;
* tensions;
* evidence.

### Vision unlocked

This changes research from search into **intellectual exploration**:

```text
Where are the interesting tensions?

Where does the idea develop?

What doesn't fit the obvious interpretation?

Which passages belong together?
```

This is the beginning of the Scholar Workbench.

---

# 5. CP4 — Real Argument Reconstruction

This is the big one for Agent ML.

### Where you are

You correctly discovered that:

```text
ArgumentProposal schema exists

but

automatic argument reconstruction does not.
```

You now have one substantive gold object:

```text
ARG-GOLD-001
```

Excellent seed.

### Do not wire the Nyāya gate as “verification” yet

First fill the argument layer with **actual propositions**.

Grow gold to:

```text
ARG-GOLD-001 ... ARG-GOLD-005
```

Then ideally 10.

Include:

```text
clear inference
implicit inference
objection/reply
reductio
ambiguous reconstruction
no-safe-reconstruction case
```

### Structures to implement/freeze now

This is important.

Do **not** make “Argument” one giant object.

Use proposition nodes + inference nodes.

```ts
interface Proposition {
  proposition_id: string;

  text: string;

  kind:
    | "TEXTUAL_CLAIM"
    | "INTERPRETIVE_CLAIM"
    | "IMPLICIT_PREMISE"
    | "CONCLUSION"
    | "OBJECTION"
    | "QUALIFICATION";

  explicitness:
    | "EXPLICIT"
    | "RECONSTRUCTED"
    | "IMPLICIT";

  grounding: Grounding[];

  boundary?: string;

  status:
    | "MACHINE_PROPOSED"
    | "EDITOR_REVIEWED"
    | "ACCEPTED"
    | "REJECTED";

  review_events: ReviewEventId[];
}
```

Then:

```ts
interface Inference {
  inference_id: string;

  premise_ids: PropositionId[];
  conclusion_ids: PropositionId[];

  scheme:
    | "NYAYA_ANUMANA"
    | "REDUCTIO"
    | "TRANSCENDENTAL"
    | "CONCEPTUAL_DISTINCTION"
    | "OBJECTION_REPLY"
    | "COUNTEREXAMPLE"
    | "OTHER";

  rationale: string;

  defeaters: Defeater[];

  status:
    | "MACHINE_PROPOSED"
    | "EDITOR_REVIEWED"
    | "ACCEPTED"
    | "REJECTED";
}
```

And:

```ts
interface Grounding {
  passage_id: PassageId;
  source_span_ids?: SourceSpanId[];

  c1_id?: C1Id;
  l200_assertion_id?: string;

  philological_proof_ids?: PhilologicalProofId[];
}
```

Finally:

```ts
interface Defeater {
  defeater_id: string;

  description: string;

  type:
    | "COUNTEREVIDENCE"
    | "RIVAL_READING"
    | "COUNTEREXAMPLE"
    | "FAILED_PREMISE"
    | "SCOPE_PROBLEM"
    | "OTHER";

  candidate_evidence_ids: string[];

  status: "PROPOSED" | "SUPPORTED" | "REJECTED";
}
```

**This is where the useful Nyāya machinery should eventually plug in.**

Not directly onto arbitrary claims.

---

# After these five, everything starts collapsing into the big vision naturally

Once CP0–CP4 are real, look what you suddenly have:

```text
Exact Sanskrit
      ↓
PhilologicalProof
      ↓
Translation
      ↓
C1
      ↓
AcceptedTheme
      ↓
Real propositions + inference
```

Now Phase 6 is no longer science fiction.

You can build:

```text
SEMANTIC VERIFICATION
```

using actual claims.

Then:

```text
discover-counterevidence
Nyāya argument audit
scope verification
polarity verification
boundary verification
```

Then:

```text
ESSAY CLAIMS
```

are derived from real arguments.

Then:

```text
essay / guide / video / podcast
```

are merely renderings.

Then:

```text
ADVERSARIAL PEER REVIEW
```

is basically orchestration over the same primitives:

```text
paper
↓
claims
↓
resolve citations
↓
retrieve evidence
↓
translation proof
↓
argument reconstruction
↓
counterevidence
↓
semantic verification
↓
review report
```

Then MCP is simply access to those capabilities.

---

# What you should implement NOW

Don't implement 30 interfaces.

I would freeze exactly these **seven canonical contracts**:

```text
1. Ref
2. ReviewState / ReviewEvent
3. BenchmarkFixture / BenchmarkRun
4. PhilologicalProof
5. EvidenceCandidate / EvidenceUse
6. Theme / ThemeMembership
7. Proposition / Inference / Grounding / Defeater
```

Everything else can sit on top.

## `Ref` is particularly important

Both agents should share a single reference type:

```ts
interface Ref {
  id: string;
  type:
    | "WORK"
    | "PASSAGE"
    | "SOURCE_SPAN"
    | "L0"
    | "TRANSLATION"
    | "C1"
    | "THEME"
    | "PROPOSITION"
    | "INFERENCE"
    | "PHILOLOGICAL_PROOF"
    | "EVIDENCE";

  version?: string;
}
```

And the invariant:

> **Every ID placed into a canonical Pāṭala object must resolve.**

No fabricated IDs.

No fuzzy locator silently promoted to IDs.

Locators can exist separately:

```ts
interface Locator {
  value: string;
  resolution_state: "RESOLVED" | "UNRESOLVED";
  resolved_id?: string;
}
```

That recent bug should permanently establish this contract.

---

# Two-agent responsibilities for the next month

### Agent L0

Only work on:

```text
CP1
PhilologicalProof
```

Immediate work:

```text
Heritage ensemble
↓
P2 disagreement analysis

then

lexical gold
↓
ranker benchmark

then

alignment gold
↓
alignment benchmark
```

Do not wander into essay logic.

---

### Agent ML

Only work on:

```text
CP0
CP2
CP3
CP4
```

Immediate work:

```text
finish benchmark gold population
↓
benchmark retrieval
↓
adjudicate 3 themes
↓
grow Argument Gold
↓
test actual extraction
```

Do **not** build the essay generator further.

Do **not** build full Bayesian propagation.

Do **not** promote the Nyāya gate to semantic verification yet.

Nyāya waits until real `Inference` objects exist.

---

# How I would put this on one screen

```text
                  NOW
                   │
        ┌──────────┴──────────┐
        │                     │
      AGENT L0             AGENT ML
        │                     │
        ▼                     ▼
 CP1 PHILOLOGICAL        CP0 BENCHMARK
      PROOF                   │
        │                     ▼
        │               CP2 RETRIEVAL
        │                     │
        │                     ▼
        │                CP3 THEMES
        │                     │
        │                     ▼
        └──────────────► CP4 ARGUMENT
                              │
                              ▼
                     SEMANTIC VERIFICATION
                              │
                              ▼
                      ADVERSARIAL REVIEW
                              │
                              ▼
                       ESSAY / WORKBENCH
                              │
                              ▼
                          API / MCP
```

The two agents **converge at CP4**.

An argument proposition can finally say:

```text
"I claim X"

because:
    C1 says...
    L2 renders...
    Sanskrit span is...
    PhilologicalProof says...
```

That is your first complete vertical scholarly object.

---

## The one sentence to keep everyone out of the weeds

Put this at the top of the roadmap:

> **The next five checkpoints are Benchmark → Philological Proof → Retrieval → Accepted Themes → Real Arguments. No new higher layer is built until the lower scholarly object it consumes has crossed its validation gate.**

Once those five are real, the big visions—scholarly companion, adversarial peer review, provenance-carrying essays, AI research workbench, API/MCP, collaborative editions—stop requiring speculative architecture.

They become **compositions of objects you already know are trustworthy.**
