Yes. After reviewing the current `agent2` branch, I think this should become the **single immediate engineering objective**.

The repo is much closer than it looks. Agent 2 has already built almost everything around the translator:

* IPVV L0/P0 is **63/63 lossless**.
* Vidyut × Heritage analysis exists and is calibrated as a witness.
* P4 L0↔L2 anchor alignment exists.
* `NEXT_VALID_ACTION(work)` and the 45-work corpus ledger exist.
* the review/correction engine exists.
* `model.py` already delegates generative work to Hermes.
* the translation state machine exists.

But there is one giant hole:

> **RAW SANSKRIT → L0 does not exist.**

The code literally has:

```text
MODE_A  AND_GLOSS       ✅
MODE_B  RAW_SANSKRIT    ❌ NOT YET BUILT
```

and raw works are deliberately blocked from Agent 3.

That should be the project now.

# The target

I would define Agent 3 v0 as:

> **Given raw Sanskrit and a registered source, autonomously produce a lossless, word/phrase-level literal analysis with every decision auditable, every uncertainty exposed, and no unsupported analysis silently promoted.**

Not yet:

> translate whole books beautifully.

First make this machine excellent:

```text
RAW SANSKRIT
      ↓
EXACT SOURCE SPANS
      ↓
TOKEN / SANDHI ANALYSIS
      ↓
LEMMA + MORPHOLOGY
      ↓
COMPOUND / PHRASE STRUCTURE
      ↓
LITERAL GLOSS
      ↓
ALTERNATIVES + UNCERTAINTY
      ↓
AUDIT / PROOF
      ↓
MACHINE_PROPOSED L0
```

Once this works, **then set it loose**.

---

# Important terminology correction

Your intuition is right, but the current repo's `L0` isn't yet exactly what you mean.

Existing IPVV L0 mostly **extracts a word/gloss layer that already exists in your translated material** and proves that extraction is lossless. The P0 harness establishes things like exact spans, coverage, ordering and round-trip integrity.

So:

```text
existing:
already-glossed IPVV
→ extract L0
→ prove extraction

what we need:
RAW SANSKRIT
→ CREATE L0
→ prove + evaluate creation
```

That distinction is crucial.

We should call the missing component something like:

```text
RAW-L0
or
L0-SOURCE-MODE
```

because `corpus_state.py` already calls it `BUILD_L0_SOURCE_MODE`.

---

# What one RAW-L0 record should contain

I would slightly expand the L0 contract.

For each actual Sanskrit unit:

```json
{
  "id": "pt:kramasadbhava:1.1:l0:007",

  "source_span": {
    "char_start": 84,
    "char_end": 97,
    "raw": "..."
  },

  "analysis": {
    "surface": "...",
    "sandhi_split": ["..."],
    "lemma": "...",
    "morphology": {
      "case": "...",
      "number": "...",
      "gender": "..."
    },
    "compound": null
  },

  "gloss": {
    "literal": "...",
    "supplied": false
  },

  "alternatives": [],

  "witnesses": {
    "vidyut": {},
    "heritage": {}
  },

  "proof": {
    "source_span": "PROVED",
    "segmentation": "SUPPORTED",
    "morphology": "SUPPORTED",
    "lexical_sense": "MACHINE_PROPOSED"
  }
}
```

The key thing is that **proof dimensions stay separate**.

We should never turn:

```text
exact source span ✅
Vidyut agrees ✅
```

into:

> therefore the English gloss is correct ✅

Those are different claims.

---

# Don't force Sanskrit into fake 1:1 English words

One architectural point matters immediately.

The product can visually appear “word-for-word,” but internally L0 needs to allow:

```text
ONE Sanskrit word → multiple English words

multiple Sanskrit elements → one semantic phrase

compound → internal constituent analysis
```

Otherwise Sanskrit compounds will destroy the representation.

So call it **word/phrase-level literal translation**.

Example conceptual shape:

```text
mahāśaktisamāveśāt

mahā + śakti + samāveśa + abl.sg.
│      │         │
great  power     immersion
                   ↓
"because of immersion in the great Power"
```

You preserve the atomic structure while allowing sensible English.

---

# The smartest thing we can do: use IPVV to train/test the factory before touching another work

This is the killer advantage of what you've already built.

You have **63 chunks whose Sanskrit→L0 relationship already exists**.

So create an experiment:

# Sanskrit-only replay

Hide all existing English from Agent 3.

Give it only:

```text
IPVV Sanskrit
+
allowed dictionaries/analyzers
+
allowed historical corpus retrieval
```

Ask it to regenerate the L0.

Then compare its proposed L0 against the existing IPVV L0.

That immediately gives us a real benchmark.

## Split it properly

Do not let it memorize the exact cases it is evaluated on.

For example:

```text
IPVV RAW-L0 benchmark

DEV
~40 chunks

EVAL
~15 chunks

LOCKED
~8 chunks
```

Better still, split by contiguous text regions so adjacent near-duplicates don't leak.

And production retrieval must be prevented from retrieving the hidden English translation of the exact evaluation passage.

That becomes the embryo of **Pāṭala Classical Sanskrit Evals**.

---

# What to evaluate

Not BLEU.

Evaluate L0 dimension-by-dimension.

### P0 — source integrity

Already essentially solved:

```text
100% source coverage
zero unknown chars
exact spans
no overlaps
stable ordering
roundtrip
```

The existing proof harness is exactly the right foundation.

### P1 — segmentation

Did it identify the actual units?

Measure things like precision/recall over gold boundaries.

### P2 — morphology

Compare:

```text
Agent selection
Vidyut
Heritage
existing reviewed analysis
```

The repo already has the ensemble machinery and knows how disagreement behaves.

### P3 — lexical/gloss fidelity

This is the new difficult layer.

Did it recover:

```text
lemma
basic sense
technical sense
negation
agency
number
case contribution
```

This is where human gold becomes especially valuable.

### P4 — literal alignment

Which Sanskrit span licenses each piece of English?

Existing P4 is already a useful starting witness but explicitly **does not prove semantic equivalence**. The repo correctly records that limitation.

### P5 later — syntax

Only add full dependency/syntax machinery when failures show that morphology + compound analysis are inadequate.

Do not architecture-max this now.

---

# How Agent 3 should actually reason

I would not have Hermes simply receive:

> translate this Sanskrit word-for-word.

That throws away the infrastructure you've built.

The loop should instead be:

```text
1. SOURCE
   get exact Sanskrit span

2. DETERMINISTIC ANALYSIS
   Vidyut candidates
   Heritage candidates

3. RETRIEVE
   dictionary / lexicon
   same-text usage
   same-author usage
   direct textual relatives
   same-school usage

4. PROPOSE
   Agent 3 chooses:
   segmentation
   lemma
   morphology
   literal gloss
   compound analysis
   alternatives

5. CHALLENGE
   separate pass tries to falsify:
   wrong lemma?
   wrong sandhi?
   wrong case?
   polarity lost?
   compound misconstrued?
   gloss too interpretive?

6. REVISE / ABSTAIN

7. VERIFY
   deterministic P0
   analyzer consistency
   schema
   provenance
   alignment

8. WRITE
   MACHINE_PROPOSED L0
```

That's an **agentic Sanskrit translator**, rather than a prompt.

---

# Critically: the model must be allowed to abstain

A batch translator that has to output one answer will poison the corpus.

The valuable behavior is:

```text
SECURE
SUPPORTED
CONFLICT
OPEN
```

Example:

```text
surface: śivātmakaḥ

lemma: śivātmaka
morphology:
  nom.sg.masc     SUPPORTED

literal:
  "having Śiva as its nature"   PREFERRED

alternatives:
  "consisting of Śiva"

lexical_sense:
  OPEN
```

Then autonomous scale is safe because ambiguity creates a **review task**, not fabricated certainty.

---

# The autonomous factory is then extremely simple

Once RAW-L0 works:

```text
                 CORPUS LEDGER
                      ↓
              NEXT_VALID_ACTION
                      ↓
                 Agent 3
                      ↓
               RAW-L0 GENERATOR
                      ↓
                   AUDIT
              ↙             ↘
           PASS             FAIL
             ↓                ↓
     MACHINE_PROPOSED      REVIEW QUEUE
             ↓
        ledger update
             ↓
       NEXT PASSAGE
```

The current state machine already provides the control-plane half of this architecture.

---

# I would actually simplify the current Agent 3 plan

The repo currently says the missing factory should go approximately:

```text
T1 → L2 → C1
```

and the older translation skill goes:

```text
T1 → R1 → T2 → R2 → T3 → T3.1 → C1
```

I would **not start there**.

That's too high-level.

Make Agent 3 v0 do only:

```text
RAW SANSKRIT
→ RAW-L0
→ audit
```

Get that frighteningly good.

Then:

```text
RAW-L0
→ CLOSE TRANSLATION
```

Then:

```text
close translation
→ adversarial reading
→ resolved translation
```

Then C1.

So the proper autonomous factory becomes:

```text
SOURCE
 ↓
L0       ← prove this first
 ↓
L1 close translation
 ↓
R1 adversary
 ↓
L2 resolved/readable
 ↓
C1 interpretation
```

The lower floor constrains the upper floor.

---

# Exact build sequence I'd give the agents

## Build 1 — `raw_l0.py`

Implement:

```text
pipeline/raw_l0.py
```

Input:

```text
work_id
passage_id
raw Sanskrit
source metadata
```

Output:

canonical L0 JSONL.

It calls:

```text
Vidyut
Heritage
Hermes/Agent3
```

but no downstream translation.

---

## Build 2 — RAW-L0 audit

Extend rather than replace `verify_l0.py`.

Keep P0 byte-level proof exactly as it is.

Add separate checks:

```text
P0 source-losslessness
P1 segmentation
P2 morphology
P3 gloss
P4 alignment
```

Never allow a semantic model score to turn a structural failure into a pass.

---

## Build 3 — IPVV Sanskrit-only replay

This is the crucial experiment.

Run Agent 3 against hidden IPVV Sanskrit.

Produce an immutable BenchmarkRun.

We want to know:

```text
segmentation accuracy
lemma accuracy
morphology accuracy
literal-gloss acceptance
technical-term acceptance
abstention quality
false-certainty rate
```

**False certainty is probably the most important metric.**

The repo already learned this lesson with P3: the rejected ranker had **100% false-certainty**, which was correctly treated as failure rather than polished output.

---

# Build 4 — human review 50–100 difficult RAW-L0 cases

Don't review thousands.

Find the failure clusters:

```text
sandhi
bahuvrīhi/tatpuruṣa ambiguity
verbal morphology
pronoun antecedents
technical terms
elliptical prose
quotation attribution
negation
```

Review those.

Every correction becomes benchmark data.

---

# Build 5 — first genuine cross-work test

Then use **Kramasadbhāva**.

Why Kramasadbhāva is ideal:

The ledger already recognizes it as raw Sanskrit, and it is currently blocked **specifically because RAW-SANSKRIT L0 mode does not exist**.

So success becomes extremely concrete:

```text
TODAY

kramasadbhava
RAW_SANSKRIT
→ BUILD_L0_SOURCE_MODE
→ BLOCKED
```

becomes:

```text
AFTER

kramasadbhava
RAW_SANSKRIT
→ GENERATE_L0
→ VERIFIED P0
→ MACHINE_PROPOSED semantic analysis
→ GENERATE_TRANSLATION
```

That proves cross-work generalization for the first time.

---

# Build 6 — only then turn on batch mode

At that point Hermes scheduling becomes boring—which is exactly what we want.

Something like:

```text
every N minutes:

query ledger

for each eligible work:
    select next untranslated passage

    run RAW-L0

    if structural audit fails:
        halt passage
        log failure

    if semantic uncertainty exceeds threshold:
        queue review
        continue

    write MACHINE_PROPOSED artifact

    update ledger
```

Do **not** batch entire works initially.

Batch passages/chunks independently with bounded retries.

One bad chunk must not corrupt or block a 30-chapter job.

---

# The threshold before “set it loose”

I would require a factory certificate along these lines:

```text
RAW-L0 FACTORY v0.1

P0 coverage                 100%
bad source spans              0
unknown source characters     0

segmentation                 measured
lemma selection              measured
morphology                   measured
literal gloss                human-rated
false certainty              below threshold
abstention precision         measured

cost / 1k Sanskrit tokens    known
review minutes / 1k tokens   known
hard failure rate            known
```

Then you can make a rational scaling decision.

The real unit economics aren't:

> "$0.04 to translate a passage."

They're:

[
C_{\text{real}}
===============

C_{\text{model}}
+
C_{\text{compute}}
+
C_{\text{human review}}
+
C_{\text{error correction}}
]

What we want Agent 3 optimizing is **review burden**, not just token cost.

---

# This changes the immediate roadmap

I would pause almost everything else for this slice.

```text
NOW
│
├── Freeze existing P0 machinery
│
├── Build RAW_SANSKRIT → L0
│
├── Sanskrit-only replay on IPVV
│
├── human-review failure cases
│
├── Kramasadbhāva first cross-work run
│
└── batch scheduler
```

Then suddenly your 45-work ledger becomes actionable.

And after that the full dream becomes believable:

```text
SOURCE CORPUS
      ↓
Agent 3 continuously consumes work
      ↓
audited L0
      ↓
close translations
      ↓
rival translations / adjudication
      ↓
C1
      ↓
arguments / themes
      ↓
Pāṭala benchmark
      ↓
Translation Audit
```

The most important point is that **you already built the safety rails before the train**. The repo's current Agent 2 architecture is explicitly designed so Agent 3 is only a worker producing candidate artifacts while Agent 2 owns corpus truth and integrity.

So yes: I would make **“RAW Sanskrit → fully audited MACHINE_PROPOSED L0” the next hard milestone, prove it blind on IPVV, then unleash it on Kramasadbhāva.** Once that works, autonomous batch translation stops being a vision and becomes a queue-processing problem.
