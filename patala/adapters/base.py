#!/usr/bin/env python3
"""patala/adapters/base.py — SourceAdapter interface.

Every adapter implements this interface:
  discover(cursor)        → DiscoveryPage
  fetch_metadata(resource) → RawObservation
  fetch_content(resource)  → RawObservation | None
  normalize(observation)   → ExtractionBundle
  changes_since(cursor)   → DiscoveryPage

"Tools don't become truth. Their outputs become observations." — newbuild
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class SourceAdapter(ABC):
    """Base adapter interface. Subclass and implement."""

    source_id: str = "base"
    adapter_version: str = "0.1.0"

    @abstractmethod
    async def discover(self, cursor: str | None = None, limit: int = 50) -> dict:
        """Enumerate resources from this source."""
        ...

    @abstractmethod
    async def fetch_metadata(self, resource: dict) -> dict:
        """Fetch metadata for a resource. Returns a RawObservation dict."""
        ...

    @abstractmethod
    async def fetch_content(self, resource: dict) -> dict | None:
        """Fetch content for a resource. Returns a RawObservation or None."""
        ...

    @abstractmethod
    async def normalize(self, observation: dict) -> dict:
        """Extract CandidateAssertions and EntityCandidates from an observation."""
        ...

    async def changes_since(self, cursor: str | None = None) -> dict:
        """Report changes since a cursor. Default: use discover."""
        return await self.discover(cursor=cursor)


def get_adapter(source_name: str) -> SourceAdapter:
    """Load an adapter by name."""
    import importlib.util
    from pathlib import Path

    adapters_dir = Path(__file__).resolve().parent
    adapter_path = adapters_dir / source_name / "adapter.py"

    if not adapter_path.exists():
        raise FileNotFoundError(f"Adapter not found: {adapter_path}")

    spec = importlib.util.spec_from_file_location(
        f"patala.adapters.{source_name}.adapter", adapter_path
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    if hasattr(mod, 'get_adapter'):
        return mod.get_adapter()

    for name in dir(mod):
        obj = getattr(mod, name)
        if isinstance(obj, type) and issubclass(obj, SourceAdapter) and obj is not SourceAdapter:
            return obj()

    raise ValueError(f"No SourceAdapter subclass found in {adapter_path}")
