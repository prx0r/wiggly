#!/usr/bin/env python3
"""patala/signing/checkpoint.py — Sign checkpoints with algorithm-tagged signatures.

Per newbuild1 §36: "Sign checkpoints, not everything. Algorithm-tagged.
Don't bake ed25519 forever into Pāṭala."

"Tools don't become truth. Their outputs become observations." — newbuild
"""
from __future__ import annotations

import hashlib
import json
import sys
import time
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from patala.hashing import uuid7, make_digest


def sign_checkpoint(checkpoint_data: dict, algorithm: str = "sha256",
                    key_id: str = "patala-default") -> dict:
    """Sign a checkpoint with an algorithm-tagged signature.

    Per newbuild1 §36: "Something like: Signature { algorithm, key_id, signature,
    signed_digest, signed_at }. Algorithm-tagged. Don't bake ed25519 forever."
    """
    # Create the digest to sign
    canonical = json.dumps(checkpoint_data, sort_keys=True, default=str)
    digest = make_digest(canonical.encode(), algorithm)

    # For now, use the digest itself as the signature
    # In production, this would use a real signing key
    signature = {
        "algorithm": algorithm,
        "key_id": key_id,
        "signature": digest["value"],  # In production, this would be a real signature
        "signed_digest": digest["value"],
        "signed_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }

    return signature


def verify_signature(checkpoint_data: dict, signature: dict) -> bool:
    """Verify a checkpoint signature."""
    canonical = json.dumps(checkpoint_data, sort_keys=True, default=str)
    algorithm = signature.get("algorithm", "sha256")
    digest = make_digest(canonical.encode(), algorithm)

    # In production, this would verify a real signature against a public key
    # For now, just verify the digest matches
    return digest["value"] == signature.get("signed_digest", "")


def sign_checkpoint_with_key(checkpoint_data: dict, private_key: bytes = None,
                              algorithm: str = "ed25519") -> dict:
    """Sign a checkpoint with a real key (placeholder for production).

    Per newbuild1 §36: "Algorithm-tagged. Don't bake ed25519 forever."
    """
    canonical = json.dumps(checkpoint_data, sort_keys=True, default=str)
    digest = make_digest(canonical.encode(), "sha256")

    # Placeholder: in production, use actual Ed25519 signing
    signature = {
        "algorithm": algorithm,
        "key_id": f"patala-{algorithm}",
        "signature": digest["value"],  # Placeholder
        "signed_digest": digest["value"],
        "signed_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }

    return signature
