# -*- coding: utf-8 -*-
import json
import os
import sqlite3
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "math_quiz.db")


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS students (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            class_name TEXT NOT NULL,
            grade TEXT NOT NULL DEFAULT '四年级下学期',
            created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS exams (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER NOT NULL,
            exam_type TEXT NOT NULL,
            score INTEGER NOT NULL DEFAULT 0,
            total INTEGER NOT NULL DEFAULT 0,
            question_ids TEXT NOT NULL DEFAULT '[]',
            submitted_at TEXT,
            created_at TEXT NOT NULL,
            FOREIGN KEY (student_id) REFERENCES students(id)
        );
        CREATE TABLE IF NOT EXISTS answers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            exam_id INTEGER NOT NULL,
            question_id INTEGER NOT NULL,
            student_answer TEXT,
            is_correct INTEGER NOT NULL DEFAULT 0,
            knowledge_point TEXT NOT NULL,
            question_text TEXT NOT NULL DEFAULT '',
            options_json TEXT NOT NULL DEFAULT '[]',
            correct_answer TEXT NOT NULL DEFAULT '',
            explanation TEXT NOT NULL DEFAULT '',
            FOREIGN KEY (exam_id) REFERENCES exams(id)
        );
    """)

    ensure_column(conn, "students", "grade", "TEXT NOT NULL DEFAULT '四年级下学期'")
    ensure_column(conn, "exams", "question_ids", "TEXT NOT NULL DEFAULT '[]'")
    ensure_column(conn, "exams", "submitted_at", "TEXT")
    ensure_column(conn, "answers", "question_text", "TEXT NOT NULL DEFAULT ''")
    ensure_column(conn, "answers", "options_json", "TEXT NOT NULL DEFAULT '[]'")
    ensure_column(conn, "answers", "correct_answer", "TEXT NOT NULL DEFAULT ''")
    ensure_column(conn, "answers", "explanation", "TEXT NOT NULL DEFAULT ''")

    conn.commit()
    conn.close()


def ensure_column(conn, table_name, column_name, column_def):
    columns = conn.execute(f"PRAGMA table_info({table_name})").fetchall()
    if any(col["name"] == column_name for col in columns):
        return
    conn.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_def}")


# ---- 学生 ----

def create_student(name, grade):
    conn = get_db()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cur = conn.execute(
        "INSERT INTO students (name, class_name, grade, created_at) VALUES (?, ?, ?, ?)",
        (name, "", grade, now),
    )
    conn.commit()
    sid = cur.lastrowid
    conn.close()
    return sid


def get_all_students():
    conn = get_db()
    rows = conn.execute("SELECT * FROM students ORDER BY created_at DESC").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_student(sid):
    conn = get_db()
    row = conn.execute("SELECT * FROM students WHERE id = ?", (sid,)).fetchone()
    conn.close()
    return dict(row) if row else None


# ---- 考试 ----

def create_exam(student_id, exam_type, question_ids):
    conn = get_db()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cur = conn.execute(
        """INSERT INTO exams (student_id, exam_type, score, total, question_ids, created_at)
           VALUES (?, ?, 0, ?, ?, ?)""",
        (student_id, exam_type, len(question_ids), json.dumps(question_ids, ensure_ascii=False), now),
    )
    exam_id = cur.lastrowid
    conn.commit()
    conn.close()
    return exam_id


def submit_exam(exam_id, answers_data):
    """answers_data: list of {question_id, student_answer, is_correct, knowledge_point}"""
    conn = get_db()
    existing = conn.execute(
        "SELECT submitted_at FROM exams WHERE id = ?",
        (exam_id,),
    ).fetchone()
    if not existing:
        conn.close()
        return None
    if existing["submitted_at"]:
        conn.close()
        return None

    correct = 0
    for a in answers_data:
        conn.execute(
            """INSERT INTO answers (
                   exam_id, question_id, student_answer, is_correct, knowledge_point,
                   question_text, options_json, correct_answer, explanation
               ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                exam_id,
                a["question_id"],
                a["student_answer"],
                a["is_correct"],
                a["knowledge_point"],
                a["question_text"],
                json.dumps(a["options"], ensure_ascii=False),
                a["correct_answer"],
                a["explanation"],
            ),
        )
        if a["is_correct"]:
            correct += 1
    conn.execute(
        "UPDATE exams SET score = ?, submitted_at = ? WHERE id = ?",
        (correct, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), exam_id),
    )
    conn.commit()
    conn.close()
    return correct


def get_exam(exam_id):
    conn = get_db()
    row = conn.execute("SELECT * FROM exams WHERE id = ?", (exam_id,)).fetchone()
    conn.close()
    exam = dict(row) if row else None
    if exam:
        exam["question_ids"] = parse_question_ids(exam.get("question_ids"))
    return exam


def get_exam_answers(exam_id):
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM answers WHERE exam_id = ? ORDER BY id", (exam_id,)
    ).fetchall()
    conn.close()
    answers = [dict(r) for r in rows]
    for answer in answers:
        answer["options"] = parse_question_ids(answer.get("options_json"))
    return answers


def get_student_exams(student_id):
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM exams WHERE student_id = ? ORDER BY created_at DESC",
        (student_id,),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_student_wrong_question_ids(student_id):
    """获取学生做错过的所有题目ID"""
    conn = get_db()
    rows = conn.execute(
        """SELECT DISTINCT a.question_id FROM answers a
           JOIN exams e ON a.exam_id = e.id
           WHERE e.student_id = ? AND a.is_correct = 0""",
        (student_id,),
    ).fetchall()
    conn.close()
    return [r["question_id"] for r in rows]


def get_student_kp_stats(student_id):
    """按知识点统计学生的正确率"""
    conn = get_db()
    rows = conn.execute(
        """SELECT a.knowledge_point,
                  COUNT(*) as total,
                  SUM(a.is_correct) as correct
           FROM answers a
           JOIN exams e ON a.exam_id = e.id
           WHERE e.student_id = ?
           GROUP BY a.knowledge_point""",
        (student_id,),
    ).fetchall()
    conn.close()
    stats = []
    for r in rows:
        total = r["total"]
        correct = r["correct"]
        rate = round(correct / total * 100) if total > 0 else 0
        stats.append({
            "kp": r["knowledge_point"],
            "total": total,
            "correct": correct,
            "rate": rate,
            "weak": rate < 60,
        })
    return stats


def parse_question_ids(raw_value):
    if not raw_value:
        return []
    try:
        value = json.loads(raw_value)
    except (TypeError, json.JSONDecodeError):
        return []
    return value if isinstance(value, list) else []
