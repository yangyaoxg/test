# -*- coding: utf-8 -*-
import json
import os
import sqlite3
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "math_quiz.db")


DIFFICULTY_WEIGHTS = {
    "basic": 1.0,
    "medium": 1.2,
    "challenge": 1.5,
}


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
            figure_svg TEXT NOT NULL DEFAULT '',
            options_json TEXT NOT NULL DEFAULT '[]',
            correct_answer TEXT NOT NULL DEFAULT '',
            explanation TEXT NOT NULL DEFAULT '',
            difficulty TEXT NOT NULL DEFAULT 'basic',
            subskill TEXT NOT NULL DEFAULT '',
            ability_tag TEXT NOT NULL DEFAULT 'calculation',
            FOREIGN KEY (exam_id) REFERENCES exams(id)
        );
    """)

    ensure_column(conn, "students", "grade", "TEXT NOT NULL DEFAULT '四年级下学期'")
    ensure_column(conn, "exams", "question_ids", "TEXT NOT NULL DEFAULT '[]'")
    ensure_column(conn, "exams", "submitted_at", "TEXT")
    ensure_column(conn, "answers", "question_text", "TEXT NOT NULL DEFAULT ''")
    ensure_column(conn, "answers", "figure_svg", "TEXT NOT NULL DEFAULT ''")
    ensure_column(conn, "answers", "options_json", "TEXT NOT NULL DEFAULT '[]'")
    ensure_column(conn, "answers", "correct_answer", "TEXT NOT NULL DEFAULT ''")
    ensure_column(conn, "answers", "explanation", "TEXT NOT NULL DEFAULT ''")
    ensure_column(conn, "answers", "difficulty", "TEXT NOT NULL DEFAULT 'basic'")
    ensure_column(conn, "answers", "subskill", "TEXT NOT NULL DEFAULT ''")
    ensure_column(conn, "answers", "ability_tag", "TEXT NOT NULL DEFAULT 'calculation'")

    conn.commit()
    conn.close()


def ensure_column(conn, table_name, column_name, column_def):
    columns = conn.execute(f"PRAGMA table_info({table_name})").fetchall()
    if any(col["name"] == column_name for col in columns):
        return
    try:
        conn.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_def}")
    except sqlite3.OperationalError as exc:
        if "duplicate column name" not in str(exc):
            raise


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
                   question_text, figure_svg, options_json, correct_answer, explanation,
                   difficulty, subskill, ability_tag
               ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                exam_id,
                a["question_id"],
                a["student_answer"],
                a["is_correct"],
                a["knowledge_point"],
                a["question_text"],
                a.get("figure_svg", ""),
                json.dumps(a["options"], ensure_ascii=False),
                a["correct_answer"],
                a["explanation"],
                a.get("difficulty", "basic"),
                a.get("subskill", ""),
                a.get("ability_tag", "calculation"),
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
        "SELECT * FROM exams WHERE student_id = ? ORDER BY created_at DESC, id DESC",
        (student_id,),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_student_question_ids_by_exam_type(student_id, exam_type):
    """获取学生某类试卷中出现过的所有题目ID。"""
    conn = get_db()
    rows = conn.execute(
        """SELECT question_ids FROM exams
           WHERE student_id = ? AND exam_type = ?""",
        (student_id, exam_type),
    ).fetchall()
    conn.close()

    seen = []
    used_ids = set()
    for row in rows:
        for question_id in parse_question_ids(row["question_ids"]):
            if question_id in used_ids:
                continue
            used_ids.add(question_id)
            seen.append(question_id)
    return seen


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
    """按知识点统计学生的掌握度。"""
    conn = get_db()
    rows = conn.execute(
        """SELECT a.knowledge_point,
                  a.is_correct,
                  a.difficulty,
                  a.subskill,
                  a.ability_tag
           FROM answers a
           JOIN exams e ON a.exam_id = e.id
           WHERE e.student_id = ?
           ORDER BY e.created_at DESC, a.id DESC""",
        (student_id,),
    ).fetchall()
    conn.close()

    grouped = {}
    for row in rows:
        kp = row["knowledge_point"]
        item = grouped.setdefault(
            kp,
            {
                "kp": kp,
                "total": 0,
                "correct": 0,
                "weighted_total": 0.0,
                "weighted_correct": 0.0,
                "ability_errors": {},
                "subskill_errors": {},
            },
        )
        weight = DIFFICULTY_WEIGHTS.get(row["difficulty"], 1.0)
        item["total"] += 1
        item["correct"] += row["is_correct"]
        item["weighted_total"] += weight
        item["weighted_correct"] += weight * row["is_correct"]

        if not row["is_correct"]:
            ability_tag = row["ability_tag"] or "calculation"
            subskill = row["subskill"] or "基础练习"
            item["ability_errors"][ability_tag] = item["ability_errors"].get(ability_tag, 0) + 1
            item["subskill_errors"][subskill] = item["subskill_errors"].get(subskill, 0) + 1

    stats = []
    for item in grouped.values():
        total = item["total"]
        correct = item["correct"]
        rate = round(correct / total * 100) if total > 0 else 0
        mastery_score = round(item["weighted_correct"] / item["weighted_total"] * 100) if item["weighted_total"] else 0

        if total < 3:
            status = "watch"
            status_label = "证据不足"
        elif mastery_score < 65:
            status = "weak"
            status_label = "优先补弱"
        elif mastery_score < 85:
            status = "watch"
            status_label = "继续巩固"
        else:
            status = "secure"
            status_label = "掌握较稳"

        weak_ability_tag = max(
            item["ability_errors"],
            key=item["ability_errors"].get,
            default="calculation",
        )
        weak_subskill = max(
            item["subskill_errors"],
            key=item["subskill_errors"].get,
            default="",
        )

        stats.append({
            "kp": item["kp"],
            "total": total,
            "correct": correct,
            "rate": rate,
            "mastery_score": mastery_score,
            "weighted_total": round(item["weighted_total"], 1),
            "weak": status == "weak",
            "status": status,
            "status_label": status_label,
            "evidence_label": "样本偏少" if total < 3 else "样本充足",
            "weak_ability_tag": weak_ability_tag,
            "weak_subskill": weak_subskill,
        })

    stats.sort(key=lambda item: (item["mastery_score"], item["total"]))
    return stats


def parse_question_ids(raw_value):
    if not raw_value:
        return []
    try:
        value = json.loads(raw_value)
    except (TypeError, json.JSONDecodeError):
        return []
    return value if isinstance(value, list) else []
