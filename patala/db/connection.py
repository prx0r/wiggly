#!/usr/bin/env python3
"""patala/db/connection.py — Postgres connection management."""
from __future__ import annotations

import os
from pathlib import Path

DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql://localhost:5432/openpatala"
)


def get_connection():
    """Get a synchronous psycopg2 connection."""
    import psycopg2
    return psycopg2.connect(DATABASE_URL)


async def get_async_connection():
    """Get an asyncpg connection."""
    import asyncpg
    return await asyncpg.connect(DATABASE_URL)
