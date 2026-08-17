#!/usr/bin/env python3
"""pipeline/harvest_to_factory.py — make the R2 harvest factory-runnable (verse extraction -> <work>.jsonl).

The harvest (47k SOURCE) is a complete identity/index layer, but the factory cannot process it yet:
factory_batch._source_objects resolves each SOURCE object's verse text by matching input_hash against a
<work>.jsonl translation file (rows: {source_sha256, sanskrit, ...}). Metadata-only records have no verse
text, so nothing advances through T1→L0→L200→C1.

This extracts real Sanskrit verses from the R2 TEI snapshots (GRETIL <lg>/<l>/<seg>, SARIT TEI) and
writes <work>.jsonl in the factory's exact format, so the harvest becomes factory-runnable.

Format (matches factory_batch._register_source + _source_objects):
    row: {work, verse_idx, source_sha256, sanskrit, translation, status, ts}
    source_sha256 = sha256(sanskrit) == the SOURCE object's input_hash
    sanskrit      = the reconstructed verse (concatenated pādas)
    oid           = <work_id>:v<verse_idx>  (matching _register_source's naming)

Usage:
  python3 pipeline/harvest_to_factory.py --source GRETIL [--dry-run] [--limit N]
  python3 pipeline/harvest_to_factory.py --source MUKTABODHA
  python3 pipeline/harvest_to_factory.py --all [--dry-run]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = Path(ROOT) / "data" / "corpus" / "downloads" / "translations"
STAGING = Path("/tmp/opencode/r2staging")

# IAST-diacritic line-detection (a "real Sanskrit verse" line)
IAST = set("āīūṛṝḷḹṃñṅśṣṭḍḥĀĪŪṚṜḶḸṀÑṄŚṢṬḌḤ")


def _sluggify(name: str) -> str:
    s = re.sub(r"[^a-zA-Z0-9]+", "_", name).strip("_").lower()
    return s[:60] or "work"


def _extract_gretil_tei(path: Path) -> list[str]:
    """Extract verses from a GRETIL TEI file (<lg> groups -> join <seg> pādas)."""
    from lxml import etree
    verses = []
    try:
        parser = etree.XMLParser(recover=True)
        tree = etree.parse(str(path), parser)
        ns = {"t": "http://www.tei-c.org/ns/1.0"}
        for lg in tree.findall(".//t:lg", ns):
            segs = [s.text or "" for s in lg.findall(".//t:seg", ns)]
            line = "".join(segs).strip()
            line = re.sub(r"\s+", " ", line)
            if line:
                verses.append(line)
        # fallback: if no lg/seg, join <l> text
        if not verses:
            for l in tree.findall(".//t:l", ns):
                t = " ".join((l.text or "").split())
                if t:
                    verses.append(t)
    except Exception as e:  # noqa: BLE001
        print(f"    (TEI parse err {path.name}: {e})")
    return verses


def _extract_sarit_tei(path: Path) -> list[str]:
    """SARIT TEI verses (<l> lines with Sanskrit text)."""
    from lxml import etree
    verses = []
    try:
        parser = etree.XMLParser(recover=True)
        tree = etree.parse(str(path), parser)
        ns = {"t": "http://www.tei-c.org/ns/1.0"}
        for l in tree.findall(".//t:l", ns):
            t = " ".join((l.text or "").split())
            if t:
                verses.append(t)
    except Exception:  # noqa: BLE001
        pass
    return verses


def _extract_muktabodha_text(path: Path) -> list[str]:
    """Muktabodha IAST: verse lines end with a numbered marker ('|| N ||' or '|| N/M ||') with prose
    interleaved. A verse line must END in the marker and have IAST diacritics in its first 40 chars."""
    verses = []
    for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = line.strip()
        # matches '|| 1 ||' and '|| 1/2 ||' (verse/sub-verse) at end of line
        if line.endswith("||") and re.search(r"\|\|\s*\d+(?:/\d+)?\s*\|\|", line):
            verse = re.sub(r"\s*\|\|\s*\d+(?:/\d+)?\s*\|\|\s*$", "", line).strip()
            verse = re.sub(r"\s+", " ", verse)
            if verse and any(ch in IAST for ch in verse[:40]):
                verses.append(verse)
    return verses


def _is_sanskrit_line(line: str) -> bool:
    return sum(1 for ch in line[:60] if ch in IAST) >= 3


DEVANAGARI = set("अआइईउऊऋएऐओऔकखगघचछजझटठडढणतथदधनपफबभमयरलवशषसह")
_DEV_NUM = "०१२३४५६७८९"


def _extract_devanagari_text(path: Path) -> list[str]:
    """Extract Devanagari verses: a line ending in ॥N॥ (Devanagari danda + number) is a verse.

    The DLI/Jivananda archive is mostly noisy Devanagari OCR. Verses are marked with ॥ N ॥ (like ||N||
    in IAST but in Devanagari script). Extract on the Devanagari marker BEFORE transliteration, so the
    OCR noise (page numbers etc.) doesn't break the marker detection. Returns Devanagari verse strings."""
    verses = []
    for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = line.strip()
        if not line.endswith("॥"):
            continue
        # strip the trailing ॥N॥ (Devanagari numerals ०-९)
        m = re.search(r"॥\s*([०१२३४५६७८९]+)\s*॥\s*$", line)
        if not m:
            continue
        verse = line[:m.start()].strip()
        verse = re.sub(r"[|¦।·]+\s*$", "", verse).strip()
        verse = re.sub(r"\s+", " ", verse)
        # a real verse has substantial Devanagari content
        if verse and sum(1 for c in verse if c in DEVANAGARI) >= 8:
            verses.append(verse)
    return verses


def extract_verses(source: str, name: str, path: Path) -> list[str]:
    if source == "GRETIL":
        return _extract_gretil_tei(path)
    if source == "SARIT":
        return _extract_sarit_tei(path)
    if source == "MUKTABODHA":
        return _extract_muktabodha_text(path)
    return []


def write_work_jsonl(work_id: str, verses: list[str], source: str, dry_run: bool = False) -> int:
    """Write <work>.jsonl in the factory's format. Returns the number of verse rows.

    Dedups exact-duplicate verses (first occurrence wins) — some source files carry a repeated second
    section (commentary quoting the text again), which would otherwise register the same verse twice."""
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    path = OUT_DIR / f"{work_id}.jsonl"
    rows = []
    seen: set[str] = set()
    for i, v in enumerate(verses):
        v = re.sub(r"\s+", " ", v).strip()
        if not v:
            continue
        if v in seen:
            continue  # exact-duplicate verse (repeated section artifact) — drop, keep first
        seen.add(v)
        v_idx = i + 1
        rows.append({
            # ── the UNIFIED verse-object (DATA-SPEC-UNIFIED) ──
            "object_id": f"{work_id}:v{v_idx}",     # work:verse — the atomic id (Model A)
            "work": work_id, "verse_idx": v_idx,
            "layer": "SOURCE",                       # the translation DAG stage (Model A)
            "version": f"{work_id}:v{v_idx}@v1",     # version chain seed (Model A)
            "superseded": False, "status": "pending",
            "source_sha256": hashlib.sha256(v.encode("utf-8")).hexdigest(),
            "sanskrit": v, "translation": "", "ts": datetime.now(timezone.utc).isoformat(),
            "_source": source,
        })
    if dry_run or not rows:
        return len(rows)
    with open(path, "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    return len(rows)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", choices=["GRETIL", "SARIT", "MUKTABODHA"])
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--limit", type=int, default=0, help="max works to process (0 = all)")
    a = ap.parse_args()

    sources = ["GRETIL", "SARIT", "MUKTABODHA"] if a.all else [a.source]
    for src in sources:
        if src in ("GRETIL", "SARIT"):
            d = STAGING / ("gretil-tei" if src == "GRETIL" else "sarit-tei")
            files = sorted(d.glob("*.xml"))
        else:
            d = STAGING / "muktabodha" / "muktabodha-lib"
            files = sorted(d.glob("*.txt"))
        print(f"[{src}] {len(files)} files")
        total_verses = total_works = 0
        for i, p in enumerate(files):
            if a.limit and i >= a.limit:
                break
            verses = extract_verses(src, p.name, p)
            if not verses:
                continue
            work_id = _sluggify(p.stem)
            n = write_work_jsonl(work_id, verses, src, dry_run=a.dry_run)
            total_verses += n
            total_works += 1
            if total_works <= 3:
                print(f"    {work_id}: {n} verses ({p.name[:40]})")
        print(f"  → {total_works} works, {total_verses} verses "
              f"({'DRY-RUN' if a.dry_run else 'written'})")


if __name__ == "__main__":
    main()
