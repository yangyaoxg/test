# -*- coding: utf-8 -*-
import os
import random
from flask import Flask, render_template, request, redirect, url_for, session
import models
from questions import (
    GRADE_OPTIONS, get_knowledge_points, get_questions_by_kp,
    get_question_by_id,
)

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "dev-secret-key-change-me")
models.init_db()


# ---- 首页：学生列表 ----

@app.route("/")
def index():
    students = models.get_all_students()
    return render_template("index.html", students=students, grade_options=GRADE_OPTIONS)


@app.route("/student/create", methods=["POST"])
def create_student():
    name = request.form.get("name", "").strip()
    grade = request.form.get("grade", "").strip()
    if name and grade:
        models.create_student(name, grade)
    return redirect(url_for("index"))


# ---- 学生详情 ----

@app.route("/student/<int:sid>")
def student_detail(sid):
    student = models.get_student(sid)
    if not student:
        return redirect(url_for("index"))
    exams = models.get_student_exams(sid)
    kp_stats = models.get_student_kp_stats(sid)
    return render_template("student.html", student=student, exams=exams, kp_stats=kp_stats)


# ---- 生成诊断卷 ----

@app.route("/exam/diagnostic/<int:sid>")
def generate_diagnostic(sid):
    student = models.get_student(sid)
    if not student:
        return redirect(url_for("index"))
    grade = student.get("grade", "四年级下学期")
    kps = get_knowledge_points(grade)
    # 40 题均匀覆盖所有知识点
    selected = []
    per_kp = 40 // len(kps)
    extra = 40 % len(kps)
    for i, kp in enumerate(kps):
        pool = get_questions_by_kp(grade, kp)
        n = per_kp + (1 if i < extra else 0)
        chosen = random.sample(pool, min(n, len(pool)))
        selected.extend(chosen)
    random.shuffle(selected)
    selected = selected[:40]

    question_ids = [q["id"] for q in selected]
    exam_id = models.create_exam(sid, "diagnostic", question_ids)
    session[f"exam_{exam_id}_questions"] = question_ids
    return render_template("exam.html", student=student, exam_id=exam_id, questions=selected, exam_type="诊断卷")


# ---- 生成补弱训练卷 ----

@app.route("/exam/training/<int:sid>")
def generate_training(sid):
    student = models.get_student(sid)
    if not student:
        return redirect(url_for("index"))
    grade = student.get("grade", "四年级下学期")
    kp_stats = models.get_student_kp_stats(sid)
    weak_kps = [s["kp"] for s in kp_stats if s["weak"]]
    if not weak_kps:
        kps = get_knowledge_points(grade)
        weak_kps = kps[:2]  # fallback

    wrong_ids = set(models.get_student_wrong_question_ids(sid))
    selected = []
    for kp in weak_kps:
        pool = get_questions_by_kp(grade, kp)
        # 优先选做错过的题
        wrong_pool = [q for q in pool if q["id"] in wrong_ids]
        other_pool = [q for q in pool if q["id"] not in wrong_ids]
        need = max(3, 15 // len(weak_kps))
        chosen = wrong_pool[:need]
        if len(chosen) < need:
            chosen.extend(random.sample(other_pool, min(need - len(chosen), len(other_pool))))
        selected.extend(chosen)

    random.shuffle(selected)
    selected = selected[:15]
    question_ids = [q["id"] for q in selected]
    exam_id = models.create_exam(sid, "training", question_ids)
    session[f"exam_{exam_id}_questions"] = question_ids
    return render_template("exam.html", student=student, exam_id=exam_id, questions=selected, exam_type="补弱训练卷")


# ---- 提交答卷 ----

@app.route("/exam/submit", methods=["POST"])
def submit_exam():
    exam_id = int(request.form.get("exam_id"))
    exam = models.get_exam(exam_id)
    if not exam:
        return redirect(url_for("index"))
    if exam.get("submitted_at"):
        return redirect(url_for("exam_result", exam_id=exam_id))

    question_ids = exam.get("question_ids") or session.get(f"exam_{exam_id}_questions", [])
    answers_data = []
    for qid in question_ids:
        q = get_question_by_id(qid)
        if not q:
            continue
        student_answer = request.form.get(f"q_{qid}", "")
        is_correct = 1 if student_answer == q["answer"] else 0
        answers_data.append({
            "question_id": qid,
            "student_answer": student_answer,
            "is_correct": is_correct,
            "knowledge_point": q["kp"],
            "question_text": q["question"],
            "options": q["options"],
            "correct_answer": q["answer"],
            "explanation": q.get("explanation", ""),
        })

    models.submit_exam(exam_id, answers_data)
    session.pop(f"exam_{exam_id}_questions", None)
    return redirect(url_for("exam_result", exam_id=exam_id))


# ---- 考试结果 ----

@app.route("/exam/result/<int:exam_id>")
def exam_result(exam_id):
    exam = models.get_exam(exam_id)
    if not exam:
        return redirect(url_for("index"))
    student = models.get_student(exam["student_id"])
    answers = models.get_exam_answers(exam_id)

    # 附上题目信息
    for a in answers:
        if a.get("question_text"):
            a["question"] = a["question_text"]
            a["correct_answer"] = a.get("correct_answer", "")
            a["explanation"] = a.get("explanation", "")
            continue

        q = get_question_by_id(a["question_id"])
        if q:
            a["question"] = q["question"]
            a["options"] = q["options"]
            a["correct_answer"] = q["answer"]
            a["explanation"] = q.get("explanation", "")

    # 按知识点统计本次考试
    kp_summary = {}
    for a in answers:
        kp = a["knowledge_point"]
        if kp not in kp_summary:
            kp_summary[kp] = {"total": 0, "correct": 0}
        kp_summary[kp]["total"] += 1
        kp_summary[kp]["correct"] += a["is_correct"]

    for kp in kp_summary:
        t = kp_summary[kp]["total"]
        c = kp_summary[kp]["correct"]
        kp_summary[kp]["rate"] = round(c / t * 100) if t > 0 else 0
        kp_summary[kp]["weak"] = kp_summary[kp]["rate"] < 60

    # 全局知识点统计
    all_kp_stats = models.get_student_kp_stats(exam["student_id"])

    return render_template(
        "result.html",
        student=student,
        exam=exam,
        answers=answers,
        kp_summary=kp_summary,
        all_kp_stats=all_kp_stats,
    )


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
