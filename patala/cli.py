#!/usr/bin/env python3
"""patala/cli.py — CLI for OpenPatala operations."""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from patala.hashing import uuid7
from patala.resolver import Resolver
from patala.events import EventStore
from patala.completeness import CompletenessCompiler
from patala.adapters.base import get_adapter
from patala.ingest import IngestionPipeline


def cmd_ingest(args):
    """Ingest data from a source adapter."""
    source = args.source
    limit = args.limit
    data_dir = Path(args.data_dir)

    print(f"Loading adapter: {source}")
    adapter = get_adapter(source)

    store_dir = data_dir / "events"
    store_dir.mkdir(parents=True, exist_ok=True)
    event_store = EventStore(store_dir)
    resolver = Resolver()
    completeness = CompletenessCompiler()

    pipeline = IngestionPipeline(adapter, event_store, resolver, completeness)
    asyncio.run(pipeline.run(limit=limit))


def cmd_serve(args):
    """Start the API server."""
    import uvicorn
    from patala.api import app
    uvicorn.run(app, host="127.0.0.1", port=args.port)


def cmd_test(args):
    """Run the conformance test."""
    from patala.conformance_test import ConformanceTest
    test = ConformanceTest()
    success = test.run_all()
    sys.exit(0 if success else 1)


def main():
    import argparse
    parser = argparse.ArgumentParser(description="OpenPatala CLI")
    sub = parser.add_subparsers(dest="command")

    # ingest
    p_ingest = sub.add_parser("ingest", help="Ingest data from a source")
    p_ingest.add_argument("--source", required=True, help="Adapter name (gretil, etc.)")
    p_ingest.add_argument("--limit", type=int, default=10, help="Max items to ingest")
    p_ingest.add_argument("--data-dir", default="data", help="Data directory")

    # serve
    p_serve = sub.add_parser("serve", help="Start API server")
    p_serve.add_argument("--port", type=int, default=8801)

    # test
    p_test = sub.add_parser("test", help="Run conformance test")

    args = parser.parse_args()
    if args.command == "ingest":
        cmd_ingest(args)
    elif args.command == "serve":
        cmd_serve(args)
    elif args.command == "test":
        cmd_test(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
