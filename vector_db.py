# vector_db.py — SQLite-based memory (replaces ChromaDB)
# Works on Streamlit Cloud with zero extra dependencies

import sqlite3
import json
import uuid
from typing import List, Dict, Any
from datetime import datetime
import os

import os
DB_PATH = os.path.join(os.path.expanduser("~"), "task_memory.db") if os.name == "nt" else "/tmp/task_memory.db"


def _get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS tasks (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            task_input TEXT NOT NULL,
            user_request TEXT NOT NULL,
            decomposition TEXT NOT NULL,
            subtask_count INTEGER DEFAULT 0,
            timestamp TEXT NOT NULL
        )
    """)
    conn.commit()
    return conn


class VectorMemory:
    def __init__(self, db_path: str = None):
        # db_path ignored — always uses /tmp on cloud
        _get_conn().close()

    def add_task(self, user_id: str, task_input: str,
                 decomposition: Dict[str, Any]) -> str:
        doc_id = str(uuid.uuid4())
        user_request = decomposition.get("user_request", task_input)
        subtask_count = len(decomposition.get("subtasks", []))
        timestamp = datetime.now().isoformat()

        with _get_conn() as conn:
            conn.execute(
                "INSERT INTO tasks VALUES (?,?,?,?,?,?,?)",
                (doc_id, user_id, task_input, user_request,
                 json.dumps(decomposition), subtask_count, timestamp)
            )
        return doc_id

    def search_similar_tasks(self, user_id: str, query: str,
                             n_results: int = 3) -> str:
        with _get_conn() as conn:
            cursor = conn.execute(
                "SELECT user_request, subtask_count, timestamp "
                "FROM tasks WHERE user_id=? ORDER BY timestamp DESC LIMIT ?",
                (user_id, n_results)
            )
            rows = cursor.fetchall()

        if not rows:
            return ""

        parts = []
        for row in rows:
            parts.append(
                f"Past Task: {row[0]}\n"
                f"Subtasks: {row[1]}\n"
                f"Date: {row[2]}"
            )
        return "\n---\n".join(parts)

    def get_user_history(self, user_id: str,
                         limit: int = 10) -> List[Dict[str, Any]]:
        with _get_conn() as conn:
            cursor = conn.execute(
                "SELECT id, task_input, user_request, subtask_count, timestamp "
                "FROM tasks WHERE user_id=? ORDER BY timestamp DESC LIMIT ?",
                (user_id, limit)
            )
            rows = cursor.fetchall()

        history = []
        for row in rows:
            ts = row[4]
            try:
                formatted = datetime.fromisoformat(ts).strftime("%Y-%m-%d %H:%M")
            except Exception:
                formatted = ts

            history.append({
                "id": row[0],
                "task_input": row[1],
                "user_request": row[2],
                "display_text": row[2][:50] + "..." if len(row[2]) > 50 else row[2],
                "subtask_count": row[3],
                "timestamp": ts,
                "formatted_time": formatted
            })
        return history

    def get_task_by_id(self, task_id: str) -> Dict[str, Any]:
        with _get_conn() as conn:
            cursor = conn.execute(
                "SELECT id, task_input, user_request, decomposition, timestamp "
                "FROM tasks WHERE id=?",
                (task_id,)
            )
            row = cursor.fetchone()

        if not row:
            return {}

        try:
            decomp = json.loads(row[3])
        except Exception:
            decomp = {}

        return {
            "id": row[0],
            "task_input": row[1],
            "user_request": row[2],
            "result": decomp,
            "timestamp": row[4]
        }

    def get_user_stats(self, user_id: str) -> Dict[str, Any]:
        with _get_conn() as conn:
            cursor = conn.execute(
                "SELECT COUNT(*), SUM(subtask_count) FROM tasks WHERE user_id=?",
                (user_id,)
            )
            row = cursor.fetchone()

        total = row[0] or 0
        total_sub = row[1] or 0
        return {
            "total_tasks": total,
            "total_subtasks": total_sub,
            "avg_subtasks_per_task": round(total_sub / total, 1) if total else 0,
            "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }

    def delete_task(self, user_id: str, task_id: str) -> bool:
        with _get_conn() as conn:
            conn.execute(
                "DELETE FROM tasks WHERE id=? AND user_id=?",
                (task_id, user_id)
            )
        return True