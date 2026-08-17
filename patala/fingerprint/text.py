#!/usr/bin/env python3
"""patala/fingerprint/text.py — Text fingerprinting (MinHash/shingles).

Per newbuildmainspec §47: "For e-texts, use much stronger identity evidence than titles:
normalized Sanskrit character shingles, MinHash, exact prefix/suffix fingerprints, passage overlap."

"Tools don't become truth. Their outputs become observations." — newbuild
"""
from __future__ import annotations

import hashlib
import re
from typing import Any


def normalize_for_fingerprint(text: str) -> str:
    """Normalize text for fingerprinting (NFC + Sanskrit normalization)."""
    import unicodedata
    normalized = unicodedata.normalize("NFC", text)
    normalized = normalized.strip()
    normalized = re.sub(r'\s+', ' ', normalized)
    # Normalize Devanagari digits
    devanagari_digits = '०१२३४५६७८९'
    for i, d in enumerate(devanagari_digits):
        normalized = normalized.replace(d, str(i))
    return normalized


def character_shingles(text: str, k: int = 3) -> list[str]:
    """Generate k-character shingles from normalized text."""
    normalized = normalize_for_fingerprint(text)
    return [normalized[i:i+k] for i in range(len(normalized) - k + 1)]


def minhash_signature(text: str, num_hashes: int = 128) -> list[int]:
    """Compute MinHash signature for near-duplicate detection.

    Per newbuildmainspec §47: "You can discover: these two differently named
    files contain 97% identical text."
    """
    shingles = character_shingles(text)
    if not shingles:
        return [0] * num_hashes

    signature = []
    for i in range(num_hashes):
        # Use different hash seeds for each component
        min_val = float('inf')
        for s in shingles:
            h = hashlib.sha256(f"{s}_{i}".encode()).hexdigest()
            val = int(h[:8], 16)
            if val < min_val:
                min_val = val
        signature.append(min_val)
    return signature


def minhash_similarity(sig1: list[int], sig2: list[int]) -> float:
    """Compute Jaccard similarity between two MinHash signatures."""
    if len(sig1) != len(sig2):
        return 0.0
    matches = sum(1 for a, b in zip(sig1, sig2) if a == b)
    return matches / len(sig1)


def prefix_suffix_fingerprint(text: str, prefix_len: int = 100, suffix_len: int = 100) -> dict:
    """Compute exact prefix/suffix fingerprints."""
    normalized = normalize_for_fingerprint(text)
    return {
        "prefix": normalized[:prefix_len],
        "suffix": normalized[-suffix_len:],
        "prefix_hash": hashlib.sha256(normalized[:prefix_len].encode()).hexdigest()[:16],
        "suffix_hash": hashlib.sha256(normalized[-suffix_len:].encode()).hexdigest()[:16],
        "length": len(normalized),
    }


def passage_overlap(text1: str, text2: str, window: int = 50) -> float:
    """Compute passage overlap between two texts."""
    words1 = set(text1.lower().split())
    words2 = set(text2.lower().split())
    if not words1 or not words2:
        return 0.0
    intersection = words1 & words2
    union = words1 | words2
    return len(intersection) / len(union) if union else 0.0


def compute_fingerprint(text: str) -> dict:
    """Compute full fingerprint for a text."""
    shingles = character_shingles(text)
    minhash = minhash_signature(text)
    prefix_suffix = prefix_suffix_fingerprint(text)

    return {
        "shingle_count": len(shingles),
        "minhash": minhash[:8],  # Store first 8 components
        "prefix": prefix_suffix["prefix"],
        "suffix": prefix_suffix["suffix"],
        "prefix_hash": prefix_suffix["prefix_hash"],
        "suffix_hash": prefix_suffix["suffix_hash"],
        "length": prefix_suffix["length"],
        "text_hash": hashlib.sha256(text.encode()).hexdigest()[:16],
    }


def similarity(fp1: dict, fp2: dict) -> float:
    """Compute similarity between two fingerprints."""
    # Compare prefix/suffix hashes
    prefix_match = fp1.get("prefix_hash") == fp2.get("prefix_hash")
    suffix_match = fp1.get("suffix_hash") == fp2.get("suffix_hash")

    # Compare length similarity
    len1 = fp1.get("length", 0)
    len2 = fp2.get("length", 0)
    len_sim = min(len1, len2) / max(len1, len2) if max(len1, len2) > 0 else 0

    return (0.4 if prefix_match else 0) + (0.4 if suffix_match else 0) + (0.2 * len_sim)
