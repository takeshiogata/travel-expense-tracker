"""SQLite/Turso database operations."""

import os
from datetime import datetime

import libsql_experimental as libsql
from dotenv import load_dotenv

from config import get_secret

load_dotenv()


_conn = None


def get_connection():
    global _conn
    url = get_secret("TURSO_DATABASE_URL")
    token = get_secret("TURSO_AUTH_TOKEN")
    if url and token:
        if _conn is None:
            _conn = libsql.connect("/tmp/expenses.db", sync_url=url, auth_token=token)
            _conn.sync()
        return _conn
    else:
        from pathlib import Path
        from config import DB_PATH
        Path(DB_PATH).parent.mkdir(parents=True, exist_ok=True)
        return libsql.connect(DB_PATH)


def _sync():
    if _conn is not None:
        _conn.sync()


def _rows_to_dicts(cursor) -> list[dict]:
    if cursor.description is None:
        return []
    columns = [d[0] for d in cursor.description]
    return [dict(zip(columns, row)) for row in cursor.fetchall()]


def _row_to_dict(cursor) -> dict | None:
    if cursor.description is None:
        return None
    columns = [d[0] for d in cursor.description]
    row = cursor.fetchone()
    return dict(zip(columns, row)) if row else None


def init_db():
    conn = get_connection()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS threads (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
            updated_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS expenses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            thread_id INTEGER NOT NULL,
            description TEXT NOT NULL,
            amount INTEGER NOT NULL,
            category TEXT NOT NULL,
            expense_date TEXT,
            created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
            FOREIGN KEY (thread_id) REFERENCES threads(id) ON DELETE CASCADE
        )
    """)
    # Migration: add expense_date column if missing
    try:
        conn.execute("ALTER TABLE expenses ADD COLUMN expense_date TEXT")
        conn.commit()
    except Exception:
        pass
    conn.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            thread_id INTEGER NOT NULL,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
            FOREIGN KEY (thread_id) REFERENCES threads(id) ON DELETE CASCADE
        )
    """)
    conn.commit()
    _sync()


# --- Thread operations ---

def create_thread(name: str | None = None) -> int:
    if name is None:
        name = datetime.now().strftime("%Y-%m-%d") + " 旅行"
    conn = get_connection()
    cur = conn.execute("INSERT INTO threads (name) VALUES (?)", (name,))
    thread_id = cur.lastrowid
    conn.commit()
    _sync()
    return thread_id


def list_threads() -> list[dict]:
    conn = get_connection()
    cur = conn.execute(
        "SELECT t.*, COALESCE(SUM(e.amount), 0) as total_amount "
        "FROM threads t LEFT JOIN expenses e ON t.id = e.thread_id "
        "GROUP BY t.id ORDER BY t.created_at DESC"
    )
    return _rows_to_dicts(cur)


def get_thread(thread_id: int) -> dict | None:
    conn = get_connection()
    cur = conn.execute("SELECT * FROM threads WHERE id = ?", (thread_id,))
    return _row_to_dict(cur)


def rename_thread(thread_id: int, new_name: str):
    conn = get_connection()
    conn.execute(
        "UPDATE threads SET name = ?, updated_at = datetime('now', 'localtime') WHERE id = ?",
        (new_name, thread_id),
    )
    conn.commit()
    _sync()


def delete_thread(thread_id: int):
    conn = get_connection()
    conn.execute("DELETE FROM threads WHERE id = ?", (thread_id,))
    conn.commit()
    _sync()


# --- Expense operations ---

def add_expense(thread_id: int, description: str, amount: int, category: str, expense_date: str | None = None) -> int:
    conn = get_connection()
    cur = conn.execute(
        "INSERT INTO expenses (thread_id, description, amount, category, expense_date) VALUES (?, ?, ?, ?, ?)",
        (thread_id, description, amount, category, expense_date),
    )
    expense_id = cur.lastrowid
    conn.execute(
        "UPDATE threads SET updated_at = datetime('now', 'localtime') WHERE id = ?",
        (thread_id,),
    )
    conn.commit()
    _sync()
    return expense_id


def get_expenses(thread_id: int) -> list[dict]:
    conn = get_connection()
    cur = conn.execute(
        "SELECT * FROM expenses WHERE thread_id = ? ORDER BY created_at ASC",
        (thread_id,),
    )
    return _rows_to_dicts(cur)


def update_expense(expense_id: int, description: str, amount: int, category: str, expense_date: str | None = None):
    conn = get_connection()
    conn.execute(
        "UPDATE expenses SET description = ?, amount = ?, category = ?, expense_date = ? WHERE id = ?",
        (description, amount, category, expense_date, expense_id),
    )
    conn.commit()
    _sync()


def find_expense_by_description(thread_id: int, description: str) -> dict | None:
    conn = get_connection()
    cur = conn.execute(
        "SELECT * FROM expenses WHERE thread_id = ? AND description LIKE ? ORDER BY created_at DESC LIMIT 1",
        (thread_id, f"%{description}%"),
    )
    return _row_to_dict(cur)


def delete_expense(expense_id: int):
    conn = get_connection()
    conn.execute("DELETE FROM expenses WHERE id = ?", (expense_id,))
    conn.commit()
    _sync()


def get_expenses_summary(thread_id: int) -> list[dict]:
    conn = get_connection()
    cur = conn.execute(
        "SELECT category, COUNT(*) as count, SUM(amount) as total "
        "FROM expenses WHERE thread_id = ? GROUP BY category ORDER BY total DESC",
        (thread_id,),
    )
    return _rows_to_dicts(cur)


# --- Message operations ---

def add_message(thread_id: int, role: str, content: str):
    conn = get_connection()
    conn.execute(
        "INSERT INTO messages (thread_id, role, content) VALUES (?, ?, ?)",
        (thread_id, role, content),
    )
    conn.commit()
    _sync()


def get_messages(thread_id: int) -> list[dict]:
    conn = get_connection()
    cur = conn.execute(
        "SELECT * FROM messages WHERE thread_id = ? ORDER BY created_at ASC",
        (thread_id,),
    )
    return _rows_to_dicts(cur)
