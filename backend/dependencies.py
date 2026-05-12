"""FastAPI dependencies for Anansi backend."""

import sqlite3
from . import database


def get_db() -> sqlite3.Connection:
    """FastAPI dependency for database connection.
    
    Provides a database connection that is properly closed after use.
    """
    conn = database.get_db()
    try:
        yield conn
    finally:
        conn.close()
