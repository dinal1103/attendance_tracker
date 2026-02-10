import sqlite3
import time
from .db_config import DB_PATH

def enable_wal():
    """Enable WAL mode for SQLite to improve concurrency."""
    try:
        conn = sqlite3.connect(DB_PATH, timeout=10, check_same_thread=False)
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.close()
    except sqlite3.Error as e:
        print(f"⚠️ Could not enable WAL mode: {e}")

enable_wal()

def get_connection():
    """Return a new SQLite connection with WAL mode enabled."""
    conn = sqlite3.connect(DB_PATH, timeout=10, check_same_thread=False)
    conn.execute("PRAGMA journal_mode=WAL;")
    return conn

def execute_query(query, params=(), retries=10, wait=1):
    """
    For INSERT/UPDATE/DELETE queries (writes).
    Retries on database lock.
    """
    for attempt in range(retries):
        try:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute(query, params)
            conn.commit()
            conn.close()
            return True, None
        except sqlite3.OperationalError as e:
            if "locked" in str(e).lower():
                # Wait and retry
                time.sleep(wait)
                continue
            return False, str(e)
    return False, "⚠️ Database is locked. Please try again."

def fetch_query(query, params=(), retries=10, wait=1):
    """
    For SELECT queries (reads).
    Retries on database lock.
    """
    for attempt in range(retries):
        try:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute(query, params)
            rows = cursor.fetchall()
            conn.close()
            return rows, None
        except sqlite3.OperationalError as e:
            if "locked" in str(e).lower():
                time.sleep(wait)
                continue
            return None, str(e)
    return None, "⚠️ Database is locked. Please try again."
