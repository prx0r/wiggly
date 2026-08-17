#!/usr/bin/env python3
"""pipeline/translation_deepfinder.py — find ACTUAL translations, not journal identity.

Journals (OpenAlex/Crossref) index scholarly articles about a work — they rarely hold the translation
itself. The actual translations live in the curated Sanskrit source repositories: OpenLibrary (edition
records with language), archive.org (scans/DLI/Hindi/English), Wisdomlib, Mahānaya/Dyczkowski,
ShivaShakti/Magee, Lakshmanjoo Academy, and the resources.ts register.

This searches those sources per work and returns translation-EDITION hits (title + language + year +
source), filtering to hits that look like a real translation/edition (eng/hin/fre/... records), NOT
journal articles. It is an ATTESTATION finder (like verify_editions.py): what was searched, what was
found, honest confidence — never a claim of scholarly verification.

Sources (politely, UA + sleep, fail-closed):
  openlibrary  — edition search by work title (fields: title/author/language/year/ebook_access)
  archive.org  — advancedsearch for "<title> translation" + DLI collection
  wisdomlib    — book pages (bilingual Sanskrit+English editions) [best-effort HTTP]
  resources.ts — the curated register (muktabodha translation-series, mahanaya, shivashakti, ...)

Usage:
  python3 pipeline/translation_deepfinder.py --work tantraloka
  python3 pipeline/translation_deepfinder.py --work tantraloka --json
  python3 pipeline/translation_deepfinder.py --works-file <json> --all
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import time
import urllib.parse
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
for p in (ROOT, ROOT / "pipeline", ROOT / "python"):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

USER_AGENT = "patala-translation-deepfinder/0.1 (mailto:dev@patala.local)"

# The curated resources that actually carry translations (subset of data/atlas/resources.ts).
TRANSLATION_SOURCES = {
    "openlibrary": "https://openlibrary.org/search.json",
    "archive.org": "https://archive.org/advancedsearch.php",
    "wisdomlib": "https://www.wisdomlib.org/hinduism/book",
    "mahanaya": "https://mahanaya.org",
    "shivashakti": "https://shivashakti.com",
}

# languages that indicate an actual translation/edition (vs the Sanskrit source text)
TRANS_LANGS = {"eng", "hin", "fre", "ger", "ita", "san+eng", "eng+san", "san,eng", "eng,san"}


def _norm(s: str) -> str:
    t = {'ā': 'a', 'ī': 'i', 'ū': 'u', 'ṛ': 'r', 'ṝ': 'r', 'ḷ': 'l', 'ḹ': 'l', 'ṃ': 'm', 'ṁ': 'm',
         'ñ': 'n', 'ṅ': 'n', 'ṇ': 'n', 'ś': 's', 'ṣ': 's', 'ṭ': 't', 'ḍ': 'd', 'ḥ': 'h'}
    return re.sub(r'[^a-z0-9 ]', '', ''.join(t.get(c, c) for c in s.lower()))


def _get_json(url: str, params: dict | list | None = None, timeout: int = 25) -> dict:
    if params:
        if isinstance(params, dict):
            url = url + "?" + urllib.parse.urlencode(params, doseq=True)
        else:
            url = url + "?" + urllib.parse.urlencode(params)  # list of (k,v) pairs keeps duplicates
    try:
        r = subprocess.run(["curl", "-s", "-m", str(timeout), "-A", USER_AGENT, url],
                           capture_output=True, text=True)
        return json.loads(r.stdout or "{}")
    except Exception as e:  # noqa: BLE001
        return {"_error": str(e)[:120]}


def openlibrary_translations(title: str, limit: int = 5) -> list[dict]:
    """Search OpenLibrary editions for a work → translation/edition records (language-tagged).

    Guards against fuzzy false-positives: the result's title must share a meaningful token with the work
    title (e.g. 'Akulavīratantra' must NOT accept 'The Kaulajñānanirṇaya'). 'Meaningful token' = a word
    >=5 chars from the work title (diacritic-folded) that appears in the result title."""
    d = _get_json("https://openlibrary.org/search.json",
                  {"q": title, "limit": limit, "fields": "title,author_name,language,ebook_access,publish_year,edition_key"})
    # the meaningful tokens of the work title (diacritic-folded, >=5 chars) we require in the result
    work_tokens = {w for w in _norm(title).split() if len(w) >= 5}
    # space-stripped form of the work title (so 'Kulārṇavatantra' matches 'Kulārṇava tantra')
    work_stripped = _norm(title).replace(" ", "")
    hits = []
    for x in d.get("docs", []):
        langs = x.get("language") or []
        langs_norm = {re.sub(r"[^a-z]", "", l.lower()) for l in langs}
        is_translation = bool(langs_norm & TRANS_LANGS)
        if not is_translation and "san" in langs_norm:
            continue  # pure Sanskrit source text — not a translation edition
        res_title = _norm(x.get("title", ""))
        # TITLE-MATCH GUARD: a meaningful work-title token must appear in the result title (or the
        # space-stripped title must contain the space-stripped work title). This rejects fuzzy matches
        # like 'Akulavīratantra' → 'The Kaulajñānanirṇaya' while keeping 'Kulārṇava tantra' ↔ 'Kulārṇavatantra'.
        token_hit = any(tok in res_title for tok in work_tokens) if work_tokens else False
        stripped_hit = len(work_stripped) >= 8 and work_stripped in res_title.replace(" ", "")
        if work_tokens and not (token_hit or stripped_hit):
            continue
        hits.append({
            "source": "openlibrary",
            "title": x.get("title", ""),
            "author": (x.get("author_name") or [""])[0],
            "language": "en" if (langs_norm & {"eng"}) else
                        ("other" if langs_norm else "unknown"),
            "year": (x.get("publish_year") or [None])[0],
            "is_translation": is_translation,
            "ebook_access": x.get("ebook_access"),
            "edition_key": (x.get("edition_key") or [""])[0],
            "url": f"https://openlibrary.org/books/{((x.get('edition_key') or [''])[0])}" if x.get("edition_key") else None,
        })
    return hits


_LANG_SIGNAL = re.compile(r"translation|english|hindi|french|fran|de la connaissance|tantra-yoga|eng$|english edition", re.I)


def archive_translations(title: str, rows: int = 6) -> list[dict]:
    """Search archive.org for translation-like items (scans/DLI/Hindi/English).

    A hit is a TRANSLATION if EITHER (a) its title signals a translation/English/Hindi/French, OR
    (b) its archive.org language metadata is eng/fre/hin (a readable edition — e.g. a DLI scan of an
    English-language edition). A bare Sanskrit-script scan (language: san, no signal) is NOT counted.
    """
    # strip author/edition words so the archive phrase matches the WORK title (not a joined blob)
    work_terms = _norm(title).split()
    core = " ".join(work_terms[:1])  # the leading work title token
    # a real work title token is >=4 chars; a 2-3 char fragment (e.g. "zzz", "sv") is noise → skip
    if len(core) < 4:
        return []
    d = _get_json("https://archive.org/advancedsearch.php",
                  [("q", f'"{core}" AND title:(translation OR english OR hindi OR french)'),
                   ("fl[]", "identifier"), ("fl[]", "title"), ("fl[]", "language"),
                   ("rows", rows), ("output", "json")])
    # fallback: if no title-marked translation, try the bare phrase and rely on language metadata
    # (catches editions like "…with the Vimarsini" whose language=eng but title lacks 'translation').
    # Only fire for a LONG-ish, distinctive core term (>=6 chars) to avoid matching unrelated items.
    if not d.get("response", {}).get("docs") and len(core) >= 6:
        d = _get_json("https://archive.org/advancedsearch.php",
                      [("q", f'"{core}"'),
                       ("fl[]", "identifier"), ("fl[]", "title"), ("fl[]", "language"),
                       ("rows", rows), ("output", "json")])
    hits = []
    for x in d.get("response", {}).get("docs", []):
        t = str(x.get("title", ""))
        raw_langs = x.get("language")
        langs = [raw_langs] if isinstance(raw_langs, str) else list(raw_langs or [])
        langs = [str(l).lower().split("-")[0] for l in langs]  # eng, san, mul, ...
        title_signal = bool(_LANG_SIGNAL.search(t))
        lang_signal = bool(set(langs) & {"eng", "fre", "hin", "ger", "ita", "spa"})
        # exclude: language purely san/mul/sa with no title signal → a Sanskrit source scan
        if not title_signal and not lang_signal:
            continue
        if set(langs) & {"san", "sa"} and not title_signal:
            continue  # Sanskrit-script scan without an explicit translation/English title
        # language: prefer explicit eng/fre/hin, else derive from title
        if "eng" in langs:
            lang = "en"
        elif "fre" in langs:
            lang = "fr"
        elif "hin" in langs:
            lang = "hi"
        elif "ger" in langs:
            lang = "de"
        else:
            lang = "en" if re.search(r"english|translation|tantra-yoga|de la connaissance", t, re.I) else (
                   "hi" if re.search(r"hindi", t, re.I) else
                   "fr" if re.search(r"fran|connaissance", t, re.I) else "unknown")
        hits.append({
            "source": "archive.org", "identifier": x.get("identifier"), "title": t[:90],
            "is_translation": True, "language": lang, "archive_languages": sorted(set(langs)),
            "url": f"https://archive.org/details/{x.get('identifier')}",
        })
    return hits


def wisdomlib_translations(title: str) -> list[dict]:
    """Wisdomlib book pages (bilingual editions). Best-effort presence check."""
    slug = _norm(title).replace(" ", "-")
    for cand in (slug, title.lower().replace(" ", "-")):
        url = f"https://www.wisdomlib.org/hinduism/book/{cand}"
        r = subprocess.run(["curl", "-s", "-m", "15", "-o", "/dev/null", "-w", "%{http_code}",
                            "-A", USER_AGENT, url], capture_output=True, text=True)
        if r.stdout.strip() == "200":
            return [{"source": "wisdomlib", "title": title, "is_translation": True,
                     "url": url, "note": "wisdomlib page exists (bilingual edition)"}]
        time.sleep(0.5)
    return []


def mahanaya_translations(title: str) -> list[dict]:
    """Mahānaya (Dyczkowski's translation site) — best-effort: a scripture page under mahanaya.org that
    carries English translation. Returns a presence hit if the page resolves 200."""
    slug = _norm(title).replace(" ", "-")
    url = f"https://mahanaya.org/en/scriptures/{slug}/"
    r = subprocess.run(["curl", "-s", "-m", "15", "-o", "/dev/null", "-w", "%{http_code}",
                        "-A", USER_AGENT, url], capture_output=True, text=True)
    if r.stdout.strip() == "200":
        return [{"source": "mahanaya", "title": title, "is_translation": True,
                 "language": "en", "url": url,
                 "note": "mahanaya.org scripture page (Dyczkowski site, English translation)"}]
    return []


# the curated translation-hosting sites (from data/atlas/resources.ts) that a work's translation
# actually lives on — these are the scholarly/publisher hosts, not journals. Each maps to a site-search
# handler below.
CURATED_TRANSLATION_SITES = {
    "anuttaratrikakula": "https://www.anuttaratrikakula.org",   # Dyczkowski (Tantrāloka etc.)
    "mahanaya": "https://mahanaya.org",                          # Dyczkowski scripture pages
    "sanskrit-trikashaivism": "https://www.sanskrit-trikashaivism.com",  # Pradīpaka translations
    "wisdomlib": "https://www.wisdomlib.org",                    # bilingual scholarly editions
    "lakshmanjoo": "https://www.lakshmanjooacademy.org",         # Lakshman Joo translations
    "vedicbooks": "https://www.vedicbooks.net",                  # Indology publisher catalog
    "sanatanlibrary": "https://www.sanatanlibrary.com",          # Sanskrit texts + translations
    "shivashakti": "https://shivashakti.com",                    # Magee Tantra translations
    "hareesh": "https://hareesh.org",                            # Christopher Wallis translations
}


def _fetch(url: str, timeout: int = 18) -> str:
    try:
        r = subprocess.run(["curl", "-s", "-L", "-m", str(timeout), "-A", USER_AGENT, url],
                           capture_output=True, text=True)
        return r.stdout or ""
    except Exception:  # noqa: BLE001
        return ""


def _wp_search(domain: str, core: str) -> list[dict]:
    """WordPress-style site search: ?s=<term>, parse article links that mention the work."""
    import html as _h
    hits = []
    for base in (domain, domain + "/en"):
        t = _fetch(f"{base}/?s={urllib.parse.quote(core)}")
        # any anchor whose text mentions the work and whose href is an on-site page
        for m in re.finditer(r'<a[^>]*href="([^"]+/[^"]*)"[^>]*>(.*?)</a>', t, re.S):
            href = _h.unescape(m.group(1))
            text = _h.unescape(re.sub("<[^>]+>", "", m.group(2))).strip()
            if core.lower() not in text.lower():
                continue
            if not (href.startswith(domain) or href.startswith("/")):
                continue
            if "#" in href or "?" in href or href.endswith((".jpg", ".png", ".pdf", ".css", ".js")):
                continue
            full = href if href.startswith(domain) else domain + href
            if any(full == x["url"] for x in hits):
                continue
            hits.append({"source": "wp", "title": text[:90], "is_translation": True,
                         "language": "en", "url": full,
                         "note": f"site search on {base}"})
        if hits:
            break
        time.sleep(0.4)
    return hits


def _vedicbooks_search(core: str) -> list[dict]:
    """vedicbooks.net (osCommerce) search → product links."""
    import html as _h
    hits = []
    t = _fetch(f"https://www.vedicbooks.net/index.php?search={urllib.parse.quote(core)}")
    for m in re.finditer(r'<a[^>]*href="([^"]*index\.php\?products_id=\d+[^"]*)"[^>]*>(.*?)</a>', t, re.S):
        href = "https://www.vedicbooks.net/" + _h.unescape(m.group(1)).replace("&amp;", "&")
        text = _h.unescape(re.sub("<[^>]+>", "", m.group(2))).strip()
        if core.lower() in text.lower() and text:
            hits.append({"source": "vedicbooks", "title": text[:90], "is_translation": True,
                         "language": "en", "url": href,
                         "note": "vedicbooks publisher-catalog product"})
        if len(hits) >= 3:
            break
    return hits


def curated_site_search(title: str) -> list[dict]:
    """Search the curated translation-hosting sites for a work via their own site-search.

    This closes the infra gap: the actual translations live on these curated scholarly/publisher sites
    (Dyczkowski, Pradīpaka, Wisdomlib, Lakshman Joo, Magee, Wallis...), but the finder only queried
    OpenLibrary + archive.org. Returns hits from any curated host whose own search surfaces the work.
    Polite: UA + sleep, fail-closed, per-site (no shared DDG rate-limit to trip).
    """
    import html as _h

    core = _norm(title).split()[0]  # leading work-title token
    hits = []

    # WordPress-based sites (anuttaratrikakula, mahanaya, sanatanlibrary, hareesh)
    for site, domain in CURATED_TRANSLATION_SITES.items():
        if site in ("vedicbooks",):
            continue  # handled separately
        for h in _wp_search(domain, core):
            if not any(h["url"] == x["url"] for x in hits):
                h["source"] = site
                hits.append(h)
        time.sleep(0.4)

    for h in _vedicbooks_search(core):
        if not any(h["url"] == x["url"] for x in hits):
            hits.append(h)

    return hits


def _variant_titles(title: str) -> list[str]:
    """Spelling variants used by archives/publishers (sv→sw, and a couple transliteration norms).
    Returns clean, pre-normalized transliterations (no diacritics) so archive search matches."""
    n = _norm(title)
    variants = []
    if "sv" in n:
        variants.append(n.replace("sv", "sw"))
    if n.startswith("isvarapratyabhij"):
        variants.append("iswarapratyabhijna")
    return [v for v in variants if v != n]


def deepfind(work_id: str, title: str, net: bool = True) -> dict:
    """Run the deep finder over all translation sources for one work."""
    results = {"work": work_id, "query_title": title, "sources": {}, "translations": []}
    if not net:
        return results

    try:
        ol = openlibrary_translations(title)
        results["sources"]["openlibrary"] = {"status": "OK", "hits": len(ol)}
        results["translations"] += ol
    except Exception as e:  # noqa: BLE001
        results["sources"]["openlibrary"] = {"status": "ERR", "error": str(e)[:100]}
    time.sleep(0.3)

    # archive.org: try the primary title, then spelling variants (sv→sw, isvarapratyabhij→iswarapratyabhij)
    ar = []
    tried = [title]
    for tq in tried + _variant_titles(title):
        try:
            ar = archive_translations(tq)
            if ar:
                break
        except Exception:  # noqa: BLE001
            ar = []
        time.sleep(0.3)
    results["sources"]["archive.org"] = {"status": "OK", "hits": len(ar), "query_variants": tried + _variant_titles(title)}
    results["translations"] += ar
    time.sleep(0.3)

    wl = wisdomlib_translations(title)
    results["sources"]["wisdomlib"] = {"status": "OK", "hits": len(wl)}
    results["translations"] += wl

    # NOTE: curated scholarly/publisher hosts (Dyczkowski, Wallis, Bäumer, ...) are added via the
    # CURATED_SUPPLEMENTS layer in build_translation_availability.py — their pages sit behind
    # site-search walls that HTML-scraping finds unreliably (course/lecture noise). The curated layer
    # records them explicitly with authority, which is the honest scholarly-verified path.

    # summary: count confirmed-translation hits (eng/hin/fre or title-marked)
    confirmed = [t for t in results["translations"] if t.get("is_translation")]
    results["confirmed_translations"] = len(confirmed)
    results["fetched_at"] = datetime.now(timezone.utc).isoformat()
    return results


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--work")
    ap.add_argument("--title", help="search title (default: derived from --work)")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--net/--no-net", dest="net", action="store_true", default=True)
    a = ap.parse_args()

    if not a.work:
        ap.error("--work required")
    title = a.title or a.work.replace("_", " ").replace("-", " ").title()
    r = deepfind(a.work, title, net=a.net)
    if a.json:
        print(json.dumps(r, indent=2, ensure_ascii=False))
    else:
        print(f"=== {a.work} («{title}») ===")
        for k, v in r["sources"].items():
            print(f"  {k}: {v.get('status')} ({v.get('hits', 0)} hits)" + (f" — {v.get('error','')}" if v.get("error") else ""))
        print(f"  → {r['confirmed_translations']} confirmed translation hits:")
        for t in r["translations"][:8]:
            if t.get("is_translation"):
                print(f"    · {t['source']:12} {t.get('title','')[:60]}  "
                      f"[{','.join(t.get('language',[])) or t.get('identifier','')}] {t.get('year') or ''}")
    return 0


if __name__ == "__main__":
    sys.exit(main())