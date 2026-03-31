from __future__ import annotations

import json
import uuid
from collections import defaultdict

from app.db import get_connection
from app.question_bank import generate_questions


def create_student(name: str, grade: str = "四年级下") -> dict:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("INSERT INTO students(name, grade) VALUES(?, ?)", (name, grade))
    student_id = cur.lastrowid
    conn.commit()
    conn.close()
    return {"id": student_id, "name": name, "grade": grade}


def generate_paper(student_id: int, paper_type: str = "diagnosis", count: int = 20, weak_points: list[str] | None = None) -> dict:
    questions = generate_questions(count=count, knowledge_points=weak_points)
    paper_id = str(uuid.uuid4())

    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO papers(id, student_id, paper_type) VALUES(?, ?, ?)",
        (paper_id, student_id, paper_type),
    )

    for idx, q in enumerate(questions, start=1):
        cur.execute(
            """
            INSERT INTO paper_questions(paper_id, idx, question_id, stem, options_json, answer, knowledge_point, explanation)
            VALUES(?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                paper_id,
                idx,
                q["id"],
                q["stem"],
                json.dumps(q["options"], ensure_ascii=False),
                q["answer"],
                q["knowledge_point"],
                q["explanation"],
            ),
        )

    conn.commit()
    conn.close()

    safe_questions = []
    for idx, q in enumerate(questions, start=1):
        safe_questions.append(
            {
                "idx": idx,
                "question_id": q["id"],
                "stem": q["stem"],
                "options": q["options"],
                "knowledge_point": q["knowledge_point"],
            }
        )

    return {"paper_id": paper_id, "paper_type": paper_type, "questions": safe_questions}


def _get_paper_questions(paper_id: str) -> list[dict]:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "SELECT idx, question_id, stem, options_json, answer, knowledge_point, explanation FROM paper_questions WHERE paper_id = ? ORDER BY idx",
        (paper_id,),
    )
    rows = cur.fetchall()
    conn.close()

    result = []
    for row in rows:
        result.append(
            {
                "idx": row["idx"],
                "question_id": row["question_id"],
                "stem": row["stem"],
                "options": json.loads(row["options_json"]),
                "answer": row["answer"],
                "knowledge_point": row["knowledge_point"],
                "explanation": row["explanation"],
            }
        )
    return result


def submit_paper(student_id: int, paper_id: str, answers: dict[str, str]) -> dict:
    questions = _get_paper_questions(paper_id)
    if not questions:
        raise ValueError("试卷不存在")

    correct = 0
    details = []
    kp_stats: dict[str, dict[str, int]] = defaultdict(lambda: {"correct": 0, "total": 0})

    for q in questions:
        idx_key = str(q["idx"])
        user_answer = (answers.get(idx_key) or "").strip().upper()
        is_correct = int(user_answer == q["answer"])
        correct += is_correct
        kp_stats[q["knowledge_point"]]["total"] += 1
        kp_stats[q["knowledge_point"]]["correct"] += is_correct

        details.append(
            {
                "idx": q["idx"],
                "stem": q["stem"],
                "knowledge_point": q["knowledge_point"],
                "user_answer": user_answer,
                "correct_answer": q["answer"],
                "is_correct": bool(is_correct),
                "explanation": q["explanation"],
            }
        )

    total = len(questions)
    score = round(correct / total * 100)

    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO submissions(paper_id, student_id, score, total) VALUES(?, ?, ?, ?)",
        (paper_id, student_id, score, total),
    )
    submission_id = cur.lastrowid

    for d in details:
        cur.execute(
            """
            INSERT INTO submission_answers(submission_id, idx, question_id, user_answer, correct_answer, is_correct, knowledge_point)
            VALUES(?, ?, ?, ?, ?, ?, ?)
            """,
            (
                submission_id,
                d["idx"],
                questions[d["idx"] - 1]["question_id"],
                d["user_answer"],
                d["correct_answer"],
                int(d["is_correct"]),
                d["knowledge_point"],
            ),
        )

    for kp, stat in kp_stats.items():
        cur.execute(
            """
            INSERT INTO knowledge_progress(student_id, knowledge_point, correct_count, total_count)
            VALUES(?, ?, ?, ?)
            ON CONFLICT(student_id, knowledge_point)
            DO UPDATE SET
                correct_count = correct_count + excluded.correct_count,
                total_count = total_count + excluded.total_count,
                updated_at = CURRENT_TIMESTAMP
            """,
            (student_id, kp, stat["correct"], stat["total"]),
        )

    conn.commit()
    conn.close()

    weak_points = []
    point_report = []
    for kp, stat in kp_stats.items():
        rate = stat["correct"] / stat["total"]
        point_report.append(
            {
                "knowledge_point": kp,
                "correct": stat["correct"],
                "total": stat["total"],
                "accuracy": round(rate * 100),
            }
        )
        if rate < 0.6:
            weak_points.append(kp)

    point_report.sort(key=lambda x: x["accuracy"])

    return {
        "paper_id": paper_id,
        "score": score,
        "correct": correct,
        "total": total,
        "weak_points": weak_points,
        "point_report": point_report,
        "details": details,
    }


def get_student_dashboard(student_id: int) -> dict:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id, name, grade, created_at FROM students WHERE id = ?", (student_id,))
    student = cur.fetchone()
    if not student:
        conn.close()
        raise ValueError("学生不存在")

    cur.execute(
        """
        SELECT knowledge_point, correct_count, total_count, updated_at
        FROM knowledge_progress
        WHERE student_id = ?
        ORDER BY total_count DESC, knowledge_point
        """,
        (student_id,),
    )
    progress_rows = cur.fetchall()

    cur.execute(
        "SELECT score, total, submitted_at FROM submissions WHERE student_id = ? ORDER BY submitted_at DESC LIMIT 10",
        (student_id,),
    )
    recent_rows = cur.fetchall()
    conn.close()

    progress = []
    for row in progress_rows:
        accuracy = round(row["correct_count"] / row["total_count"] * 100) if row["total_count"] else 0
        progress.append(
            {
                "knowledge_point": row["knowledge_point"],
                "correct_count": row["correct_count"],
                "total_count": row["total_count"],
                "accuracy": accuracy,
                "updated_at": row["updated_at"],
            }
        )

    return {
        "student": dict(student),
        "progress": progress,
        "recent_submissions": [dict(row) for row in recent_rows],
    }
