from __future__ import annotations

import sqlite3
from pathlib import Path

DB_PATH = Path("data/app.db")


def get_connection() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    conn = get_connection()
    cur = conn.cursor()

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS students (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            grade TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """
    )

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS papers (
            id TEXT PRIMARY KEY,
            student_id INTEGER NOT NULL,
            paper_type TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(student_id) REFERENCES students(id)
        )
        """
    )

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS paper_questions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            paper_id TEXT NOT NULL,
            idx INTEGER NOT NULL,
            question_id TEXT NOT NULL,
            stem TEXT NOT NULL,
            options_json TEXT NOT NULL,
            answer TEXT NOT NULL,
            knowledge_point TEXT NOT NULL,
            explanation TEXT NOT NULL,
            FOREIGN KEY(paper_id) REFERENCES papers(id)
        )
        """
    )

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS submissions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            paper_id TEXT NOT NULL,
            student_id INTEGER NOT NULL,
            score INTEGER NOT NULL,
            total INTEGER NOT NULL,
            submitted_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(paper_id) REFERENCES papers(id),
            FOREIGN KEY(student_id) REFERENCES students(id)
        )
        """
    )

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS submission_answers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            submission_id INTEGER NOT NULL,
            idx INTEGER NOT NULL,
            question_id TEXT NOT NULL,
            user_answer TEXT,
            correct_answer TEXT NOT NULL,
            is_correct INTEGER NOT NULL,
            knowledge_point TEXT NOT NULL,
            FOREIGN KEY(submission_id) REFERENCES submissions(id)
        )
        """
    )

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS knowledge_progress (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER NOT NULL,
            knowledge_point TEXT NOT NULL,
            correct_count INTEGER NOT NULL DEFAULT 0,
            total_count INTEGER NOT NULL DEFAULT 0,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(student_id, knowledge_point),
            FOREIGN KEY(student_id) REFERENCES students(id)
        )
        """
    )

    conn.commit()
    conn.close()
