"""Read-only connection to the reference database.

DATABASE_URL comes from .env in the project root (see .env.example).
"""

import os
from datetime import date, datetime
from decimal import Decimal
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

ROOT = Path(__file__).resolve().parents[3]
load_dotenv(ROOT / ".env")


@lru_cache(maxsize=1)
def get_engine() -> Engine:
    """One engine (with its connection pool) per process, created on first use."""
    url = os.getenv("DATABASE_URL")
    if not url:
        raise RuntimeError("DATABASE_URL is not set: copy .env.example to .env and fill it in")
    return create_engine(url, pool_pre_ping=True, pool_size=5)


def _jsonable(value):
    """Database types that json.dumps cannot handle -> plain Python types."""
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    return value


def fetch_all(sql: str, **params) -> list[dict]:
    """Run one parameterised query; values are passed separately, never pasted into the SQL."""
    with get_engine().connect() as conn:
        rows = conn.execute(text(sql), params).mappings()
        return [{key: _jsonable(value) for key, value in row.items()} for row in rows]
