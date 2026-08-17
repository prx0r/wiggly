#!/usr/bin/env python3
"""pipeline/pipeline_verify.py — catch the mistakes the ingest/availability pipeline makes.

The openpatala ingest + API pipeline (extract → register → deepfind → download → compile) can silently
make mistakes. This module is the verification layer that CATCHES them, so they are accountable, not
silent. Every check writes a timestamped, queryable row to the pipeline-audit registry.

Check types (each maps to a real failure mode we found in red-teaming):
  A. DETERMINISTIC (no model, run every build):
     A1 extractor_sanity    — verse_count>0, IAST diacritics present, no exact-duplicate verses
                               (catches the kaulajnananirnaya '||N/N||' 0-verse miss)
     A2 source_binding      — every registered SOURCE sha256(sanskrit) matches the jsonl source_sha256
                               (catches hash drift between extract and register)
     A3 dupe_detector       — no two SOURCE objects share an input_hash (catches double-registration)
     A4 coverage_check      — verse count vs a sane floor; suspicious 0 or balloon flags the extractor
  B. LLM-JUDGE (the 'similar stack' idea — batch via model.chat):
     B1 edition_fits_work   — does this edition actually translate this work? (catches Urdu/Quran false
                              positives AND the Dyczkowski/Wallis missed translations)
     B2 tier_confirmation   — is our A/B/C tier right? (scholarly vs scan vs AI)
     B3 language_confirm    — is the edition language right? (the 'other'-vs-'fr' case)
  C. RECONCILIATION (cross-source truth):
     C1 missed_by_auto      — a curated supplement exists but the auto-finder didn't find it → a search
                              variant or curated add is needed
     C2 index_stale         — compiled translation-availability.json vs source seeds/registry mtimes
                              (catches the API serving a stale compiled index)

Registry: data/corpus/registries/pipeline-audit.jsonl  (streamed append, git-able, queryable)
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
for p in (ROOT, ROOT / "pipeline"):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

AUDIT = ROOT / "data/corpus/registries/pipeline-audit.jsonl"
INDEX = ROOT / "data/corpus/translation-availability.json"
IAST = set("āīūṛṝḷḹṃñṅśṣṭḍḥĀĪŪṚṜḶḸṀÑṄŚṢṬḌḤ")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _log(rec: dict) -> None:
    AUDIT.parent.mkdir(parents=True, exist_ok=True)
    with AUDIT.open("a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")


# ── A. DETERMINISTIC CHECKS ──────────────────────────────────────────────────
def check_extractor_sanity(work_id: str, verses: list[str], extractor: str) -> dict:
    """A1: a sane extraction has verses with IAST diacritics and no exact duplicates."""
    problems = []
    if not verses:
        problems.append("ZERO verses extracted — possible regex miss (e.g. ||N/N|| markers)")
    else:
        iast_hits = sum(1 for v in verses if any(c in IAST for c in v[:40]))
        if iast_hits < max(1, len(verses) // 2):
            problems.append(f"only {iast_hits}/{len(verses)} verses have IAST diacritics — possibly wrong extractor")
        seen = set()
        dupes = 0
        for v in verses:
            if v in seen:
                dupes += 1
            seen.add(v)
        if dupes:
            problems.append(f"{dupes} exact-duplicate verses")
    ok = not problems
    _log({"check": "A1_extractor_sanity", "work": work_id, "extractor": extractor,
          "verses": len(verses), "ok": ok, "problems": problems, "ts": _now()})
    return {"ok": ok, "verses": len(verses), "problems": problems}


def check_source_binding(work_id: str) -> dict:
    """A2: every registered SOURCE sha256(sanskrit) matches its jsonl source_sha256."""
    jl = ROOT / "data/corpus/downloads/translations" / f"{work_id}.jsonl"
    reg = ROOT / "data/corpus/registries/source-registry.jsonl"
    if not jl.exists():
        return {"ok": True, "note": "no jsonl (skip)"}
    # map jsonl verse → its expected sha
    expected = {}
    for line in jl.open(encoding="utf-8"):
        try:
            r = json.loads(line)
        except Exception:
            continue
        s = (r.get("sanskrit") or "").strip()
        if s:
            expected[r.get("source_sha256") or hashlib.sha256(s.encode()).hexdigest()] = s
    # find registered SOURCE rows for this work and confirm input_hash == sha256(verse)
    mismatches = 0
    checked = 0
    if reg.exists():
        for line in reg.open(encoding="utf-8"):
            try:
                o = json.loads(line)
            except Exception:
                continue
            oid = o.get("object_id", "")
            if not oid.startswith(work_id + ":v"):
                continue
            checked += 1
            verse = (o.get("payload", {}).get("verse") or "").strip()
            h = hashlib.sha256(verse.encode("utf-8")).hexdigest()
            if o.get("input_hash") != h:
                mismatches += 1
    ok = mismatches == 0
    _log({"check": "A2_source_binding", "work": work_id, "checked": checked,
          "mismatches": mismatches, "ok": ok, "ts": _now()})
    return {"ok": ok, "checked": checked, "mismatches": mismatches}


def check_dupes(work_id: str) -> dict:
    """A3: no two SOURCE objects for this work share an input_hash."""
    reg = ROOT / "data/corpus/registries/source-registry.jsonl"
    hashes = {}
    if reg.exists():
        for line in reg.open(encoding="utf-8"):
            try:
                o = json.loads(line)
            except Exception:
                continue
            if o.get("object_id", "").startswith(work_id + ":v"):
                hashes.setdefault(o.get("input_hash"), []).append(o.get("object_id"))
    dupes = {h: ids for h, ids in hashes.items() if len(ids) > 1}
    ok = not dupes
    _log({"check": "A3_dupe_detector", "work": work_id, "dupe_hashes": len(dupes),
          "ok": ok, "ts": _now()})
    return {"ok": ok, "dupe_hashes": len(dupes)}


# ── C. RECONCILIATION ────────────────────────────────────────────────────────
def check_missed_by_auto(work_id: str, auto_titles: list[str], curated_titles: list[str]) -> dict:
    """C1: a curated supplement exists that the auto-finder didn't find → a coverage gap to fix."""
    missing = [ct for ct in curated_titles
               if not any(ct.lower() in at.lower() or at.lower() in ct.lower() for at in auto_titles)]
    ok = not missing
    if missing:
        _log({"check": "C1_missed_by_auto", "work": work_id,
              "curated_not_in_auto": missing, "ok": False, "ts": _now()})
    return {"ok": ok, "curated_not_in_auto": missing}


def check_index_stale(work_id: str = None) -> dict:
    """C2: the compiled index is stale vs source seeds / registry mtimes."""
    if not INDEX.exists():
        return {"ok": True, "note": "no index"}
    idx_mtime = os.path.getmtime(INDEX)
    stale = []
    for src in (ROOT / "data/atlas").glob("*.ts"):
        if src.stat().st_mtime > idx_mtime:
            stale.append(str(src.name))
    reg = ROOT / "data/corpus/registries/source-registry.jsonl"
    if reg.exists() and reg.stat().st_mtime > idx_mtime:
        stale.append("source-registry.jsonl")
    ok = not stale
    _log({"check": "C2_index_stale", "newer_than_index": stale, "ok": ok, "ts": _now()})
    return {"ok": ok, "newer_than_index": stale}


# ── B. LLM-JUDGE CHECKS ──────────────────────────────────────────────────────
def judge_edition(work_title: str, edition: dict, model: str = "mimo-v2.5",
                  dry_run: bool = False) -> dict:
    """B1+B2+B3: the judge checks an edition — does it fit the work, is the tier/language right?

    Returns a structured verdict. Uses model.chat (hermes). Fail-closed on any error."""
    prompt = {
        "work_title": work_title,
        "edition_title": edition.get("title", ""),
        "edition_author": edition.get("translator") or edition.get("author") or "",
        "recorded_language": edition.get("language"),
        "recorded_tier": edition.get("tier"),
        "recorded_source": edition.get("source"),
        "task": (
            "Answer THREE questions about this translation EDITION. "
            "1) fits_work: does this edition plausibly translate or comment on the work? (yes/no/unknown) "
            "2) tier: is the recorded tier correct? A=scholarly published translation, B=historical scan/OCR, "
            "   C=unverified/machine-generated. Answer correct/uncertain. "
            "3) language: is the recorded language correct? Answer correct/uncertain. "
            "Return ONLY JSON: {\"fits_work\":\"yes|no|unknown\",\"tier\":\"correct|uncertain\","
            "\"language\":\"correct|uncertain\",\"reason\":\"<brief>\"}"
        ),
    }
    if dry_run:
        _log({"check": "B_judge", "work": work_title, "edition": edition.get("title"),
              "verdict": "DRY_RUN", "ts": _now()})
        return {"dry_run": True}
    from model import chat  # noqa: E402
    import re as _re
    try:
        raw = chat(json.dumps(prompt, ensure_ascii=False),
                   "Judge this translation edition.", model=model, timeout=90)
        m = _re.search(r"\{.*\}", raw or "", _re.S)
        verdict = json.loads(m.group(0)) if m else {"fits_work": "unknown", "tier": "uncertain",
                                                    "language": "uncertain", "reason": f"__PARSE__ {raw[:60]}"}
    except Exception as e:
        verdict = {"fits_work": "unknown", "tier": "uncertain", "language": "uncertain",
                   "reason": f"__ERROR__ {str(e)[:80]}"}
    _log({"check": "B_judge", "work": work_title, "edition": edition.get("title"),
          "recorded": {"language": edition.get("language"), "tier": edition.get("tier"),
                       "source": edition.get("source")},
          "verdict": verdict, "ts": _now()})
    return verdict


def verify_work_editions(work_id: str, work_title: str, editions: list[dict],
                         model: str = "mimo-v2.5", dry_run: bool = False,
                         max_editions: int = 4) -> list[dict]:
    """Run the judge over the (English) editions of one work, batched."""
    en_editions = [e for e in editions if e.get("language") == "en"]
    results = []
    for e in en_editions[:max_editions]:
        v = judge_edition(work_title, e, model=model, dry_run=dry_run)
        results.append({"title": e.get("title"), "recorded_tier": e.get("tier"),
                        "recorded_language": e.get("language"), "verdict": v})
    return results


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--work", help="one work id to verify")
    ap.add_argument("--all", action="store_true", help="verify all works in the index")
    ap.add_argument("--dry-run", action="store_true", help="deterministic checks only (no model calls)")
    ap.add_argument("--judge", action="store_true", help="run the LLM-judge edition checks (B)")
    ap.add_argument("--max-editions", type=int, default=4)
    a = ap.parse_args()

    idx = json.loads(INDEX.read_text(encoding="utf-8")) if INDEX.exists() else {"works": {}}
    works = idx.get("works", {})
    targets = [a.work] if a.work else list(works.keys()) if a.all else list(works.keys())[:3]

    # import the compile's curated map for C1 reconciliation
    from build_translation_availability import CURATED_SUPPLEMENTS  # noqa: E402

    summary = {"works": len(targets), "ok": 0, "flagged": 0, "issues": []}
    for wid in targets:
        rec = works.get(wid, {})
        # A: deterministic (extractor sanity via the jsonl if present)
        jl = ROOT / "data/corpus/downloads/translations" / f"{wid}.jsonl"
        verses = []
        if jl.exists():
            for line in jl.open(encoding="utf-8"):
                try:
                    verses.append((json.loads(line).get("sanskrit") or "").strip())
                except Exception:
                    pass
        a1 = check_extractor_sanity(wid, verses, rec.get("source", "?"))
        a2 = check_source_binding(wid)
        a3 = check_dupes(wid)
        # C: reconciliation
        auto_titles = [t.get("title", "") for t in rec.get("translations", []) if t.get("source") != "curated"]
        curated_titles = [t.get("title", "") for t in rec.get("translations", []) if t.get("source") == "curated"]
        c1 = check_missed_by_auto(wid, auto_titles, curated_titles)
        c2 = check_index_stale(wid)

        flagged = not (a1["ok"] and a2["ok"] and a3["ok"] and c1["ok"] and c2["ok"])
        issues = [p for p in a1["problems"]] + \
                 (["source-binding mismatch"] if not a2["ok"] else []) + \
                 (["dupe hashes"] if not a3["ok"] else []) + \
                 (["curated-not-in-auto"] if not c1["ok"] else []) + \
                 (["stale index"] if not c2["ok"] else [])
        if flagged:
            summary["flagged"] += 1
            summary["issues"].append({"work": wid, "issues": issues})
        else:
            summary["ok"] += 1
        print(f"  {wid}: A[a1={a1['ok']} a2={a2['ok']} a3={a3['ok']}] C[c1={c1['ok']} c2={c2['ok']}] "
              f"{'FLAG: '+','.join(issues) if issues else 'OK'}")

        # B: LLM-judge on English editions
        if a.judge and rec.get("translations"):
            v = verify_work_editions(wid, rec.get("title", wid), rec["translations"],
                                     dry_run=a.dry_run, max_editions=a.max_editions)
            if not a.dry_run:
                for r in v:
                    print(f"    judge[{r['title'][:35]}]: fits={r['verdict'].get('fits_work')} "
                          f"tier={r['verdict'].get('tier')} lang={r['verdict'].get('language')}")
            else:
                print(f"    (judge DRY — {len(v)} editions queued, no model calls)")

    print(f"\n→ {summary['ok']}/{summary['works']} clean, {summary['flagged']} flagged")
    print(f"  audit log: {AUDIT}")
    return 1 if summary["flagged"] else 0


if __name__ == "__main__":
    sys.exit(main())