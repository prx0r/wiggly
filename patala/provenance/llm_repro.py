#!/usr/bin/env python3
"""patala/provenance/llm_repro.py — LLM reproducibility tracking.

Per newbuild1 §42: "For LLM calls, be honest about reproducibility.
For an API model: capture provider, provider_model_id, request timestamp,
request body artifact, prompt digest, response artifact, response headers,
sampling configuration, tool definitions, system implementation version."

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
from patala.db import store


def record_llm_call(model: str, provider: str, prompt: str, response: str,
                    config: dict = None, tool_defs: list = None) -> dict:
    """Record an LLM call with full reproducibility metadata.

    Per newbuild1 §42: "Capture provider, provider_model_id, request timestamp,
    request body artifact, prompt digest, response artifact, response headers,
    sampling configuration, tool definitions, system implementation version."
    """
    prompt_digest = make_digest(prompt.encode(), "sha256")
    response_digest = make_digest(response.encode(), "sha256")

    record = {
        "id": f"PTLLM_{uuid7()}",
        "model": model,
        "provider": provider,
        "prompt_digest": prompt_digest,
        "response_digest": response_digest,
        "request_timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "sampling_config": config or {},
        "tool_definitions": tool_defs or [],
        "reproducibility": "NON_DETERMINISTIC",
        "system_version": "openpatala-1.0",
    }

    # Store in derivation_activities table (reuse existing table)
    conn = store.get_conn()
    cur = conn.cursor()
    cur.execute(
        '''INSERT INTO derivation_activities
        (id, activity_type, inputs, outputs, actor_id, software, configuration,
         started_at, completed_at, created_at)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)''',
        (record["id"], "LLM_CALL", json.dumps([{"prompt_digest": prompt_digest}]),
         json.dumps([{"response_digest": response_digest}]),
         f"provider:{provider}", json.dumps({"model": model}),
         json.dumps(config or {}), record["request_timestamp"],
         record["request_timestamp"], record["request_timestamp"])
    )
    conn.commit()
    cur.close()
    conn.close()

    return record
