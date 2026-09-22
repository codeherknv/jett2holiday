"""
Database connection helper for SQLite (APS-02.db).
Provides connection lifecycle management and connection pooling/factory for FastAPI.
"""

import os
import sqlite3
from typing import Generator
from pathlib import Path

# Resolve path to /data/APS-02.db relative to repository root
DEFAULT_DB_PATH = Path(__file__).resolve().parent.parent.parent / "data" / "APS-02.db"
DB_PATH = os.getenv("DATABASE_URL", str(DEFAULT_DB_PATH))


def get_db_connection() -> sqlite3.Connection:
    """
    Creates and returns a raw SQLite connection with row factory enabled.
    
    TODO [Phase 2]: Add connection pooling or read-only/read-write pragma tuning
    (e.g., WAL mode, busy timeout, cache size) for high throughput during pricing event ingestion.
    """
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def get_db() -> Generator[sqlite3.Connection, None, None]:
    """
    FastAPI dependency yielding a database connection per request.
    
    Usage:
        @app.get("/some-route")
        def route_handler(db: sqlite3.Connection = Depends(get_db)):
            ...
    """
    conn = get_db_connection()
    try:
        yield conn
    finally:
        conn.close()
