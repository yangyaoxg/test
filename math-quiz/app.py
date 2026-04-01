# -*- coding: utf-8 -*-
import os
from datetime import datetime, timedelta
from collections import defaultdict
from flask import Flask, render_template, request, redirect, url_for, session
import models
from questions import (
    EXAM_TARGETS,
    GRADE_OPTIONS,
    build_diagnostic_questions,
    build_training_questions,
    get_syllabus_knowledge_points,
    get_question_by_id,
)

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "dev-secret-key-change-me")
models.init_db()


ABILITY_RECOMMENDATIONS = {
    "concept": "先做概念辨析和定义判断，避免会算但不会判。",
    "calculation": "先补基础算理和步骤规范，再做同类变式。",
    "application": "加强情境题信息提取和数量关系建模。",
}


KNOWLEDGE_POINT_METHODS = {
    "四则运算": "先看有没有括号，再按“先乘除、后加减”的顺序计算；同级运算按从左到右依次算。",
    "小数的意义和性质": "先弄清每一位上的计数单位，再判断末尾 0、分数改写或单位换算后的结果。",
    "小数的加法和减法": "把小数点对齐，也就是把相同数位对齐，再从低位算起。",
    "三角形": "抓住三角形的基本性质，比如边的关系、角的关系和内角和，再进行判断。",
    "平均数与条形统计图": "先找“总量”和“份数”的关系，平均数通常用“总量 ÷ 份数”来求。",
    "万以内加减法": "按数位对齐后再计算，个位、十位、百位依次相加或相减，需要时注意进位和退位。",
    "乘法与除法": "先判断是求几个几，还是平均分，再选择乘法或除法；有余数题要用“被除数 = 除数 × 商 + 余数”。",
    "时分秒": "先统一时间单位，再做加减计算；涉及时刻时要看清开始时刻和经过时间。",
    "长方形和正方形": "先分清题目求的是周长还是面积，再套用对应公式，最后别忘了写单位。",
    "分数的初步认识": "先看整体被平均分成几份，这就是分母；取了几份，这就是分子。",
    "小数乘法": "先按整数乘法计算，再根据两个因数一共有几位小数确定积的小数点位置。",
    "小数除法": "先把除数转化成整数，再按照整数除法去算，最后确定商的小数点位置。",
    "因数与倍数": "先根据整除关系判断，再结合因数、倍数、质数、合数、公因数和公倍数的定义作答。",
    "多边形面积": "先认清图形，再选对应面积公式；如果题目求底、高或宽，就用逆向思考把公式变形。",
    "简易方程": "把未知数单独留在等号一边，另一边做相反运算，最后记得检验。",
    "分数乘法": "整数与分数相乘可以看成“求一个数的几分之几”；分数乘分数用分子乘分子、分母乘分母。",
    "分数除法": "除以一个分数，转化成乘它的倒数，再按分数乘法计算。",
    "百分数": "先把百分数和分数、小数互相转化，再结合“现价、原价、增加、减少”等关系求解。",
    "圆": "先分清半径、直径、周长和面积，再选择正确公式进行计算。",
    "比和比例": "先看两个量之间的对应关系，再用化简比、求比值或比例基本性质解题。",
}


KNOWLEDGE_POINT_PITFALLS = {
    "四则运算": "最容易错在运算顺序，尤其是看到加减就急着先算，或者漏掉括号。",
    "小数的意义和性质": "注意小数末尾的 0 去掉后大小不变，但中间的 0 不能随便去掉。",
    "小数的加法和减法": "不要只把末尾对齐，一定要把小数点对齐；整数也可以补 0 后再算。",
    "三角形": "判断边和角时不要凭感觉，要用三角形的性质逐条验证。",
    "平均数与条形统计图": "不要把平均数当成其中某一个数，关键是先求总量再平均分。",
    "万以内加减法": "退位和进位最容易漏掉，算完后可以用估算检查结果是否合理。",
    "乘法与除法": "先分清是平均分、包含除还是求总数，避免把乘除法列反。",
    "时分秒": "做题前先统一单位，像“分”和“秒”、“时”和“分”混在一起时特别容易出错。",
    "长方形和正方形": "周长和面积公式不要混用，最后还要检查单位是不是对应正确。",
    "分数的初步认识": "只有“平均分”才能用分数表示，分子和分母的位置也不能写反。",
    "小数乘法": "最常见的错误是小数点点错位置，算完要估一估结果大小。",
    "小数除法": "转化时被除数和除数要同时扩大相同倍数，不能只移动一边的小数点。",
    "因数与倍数": "因数和倍数是相互依存的，判断时要看是不是整除。",
    "多边形面积": "面积题常见错误是公式记混，或者算出结果后漏写平方单位。",
    "简易方程": "移项思路不适合小学写法，按‘等式两边同时做同样的运算’更规范。",
    "分数乘法": "能约分时尽量先约分，既能减少计算量，也能降低出错概率。",
    "分数除法": "不要忘记是‘除以一个分数乘它的倒数’，不是只把前一个分数颠倒。",
    "百分数": "百分数应用题最怕把单位‘1’找错，先判断谁是原来的量。",
    "圆": "半径和直径、周长和面积这两组概念最容易混淆，审题时要先分清。",
    "比和比例": "比的前项后项不能随便交换，比例题还要注意对应量是否一致。",
}


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
    summary = build_student_summary(kp_stats)
    syllabus_kps = get_syllabus_knowledge_points(student.get("grade", "四年级下学期"))
    trend_summary = build_recent_diagnostic_trend(exams)
    activity_calendar = build_activity_calendar(exams)
    growth_badges = build_growth_badges(exams, summary, kp_stats, activity_calendar)
    engagement_summary = build_engagement_summary(exams)
    today_mission = build_today_mission(student, summary, engagement_summary)
    return render_template(
        "student.html",
        student=student,
        exams=exams,
        kp_stats=kp_stats,
        summary=summary,
        syllabus_kps=syllabus_kps,
        trend_summary=trend_summary,
        growth_badges=growth_badges,
        engagement_summary=engagement_summary,
        activity_calendar=activity_calendar,
        today_mission=today_mission,
    )


# ---- 生成诊断卷 ----

@app.route("/exam/diagnostic/<int:sid>")
def generate_diagnostic(sid):
    student = models.get_student(sid)
    if not student:
        return redirect(url_for("index"))
    grade = student.get("grade", "四年级下学期")
    historical_question_ids = models.get_student_question_ids_by_exam_type(sid, "diagnostic")
    selected = build_diagnostic_questions(
        grade,
        EXAM_TARGETS["diagnostic"],
        excluded_ids=historical_question_ids,
    )
    syllabus_kps = get_syllabus_knowledge_points(grade)
    covered_kps = []
    seen = set()
    for question in selected:
        if question["kp"] in seen:
            continue
        seen.add(question["kp"])
        covered_kps.append(question["kp"])
    coverage_rows = build_exam_coverage_rows(selected, syllabus_kps)

    question_ids = [q["id"] for q in selected]
    exam_id = models.create_exam(sid, "diagnostic", question_ids)
    session[f"exam_{exam_id}_questions"] = question_ids
    return render_template(
        "exam.html",
        student=student,
        exam_id=exam_id,
        questions=selected,
        exam_type="诊断卷",
        syllabus_kps=syllabus_kps,
        covered_kps=covered_kps,
        coverage_rows=coverage_rows,
    )


# ---- 生成补弱训练卷 ----

@app.route("/exam/training/<int:sid>")
def generate_training(sid):
    student = models.get_student(sid)
    if not student:
        return redirect(url_for("index"))
    grade = student.get("grade", "四年级下学期")
    kp_stats = models.get_student_kp_stats(sid)
    wrong_ids = set(models.get_student_wrong_question_ids(sid))
    selected = build_training_questions(grade, kp_stats, wrong_ids, EXAM_TARGETS["training"])
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
            "figure_svg": q.get("figure_svg", ""),
            "options": q["options"],
            "correct_answer": q["answer"],
            "explanation": q.get("explanation", ""),
            "difficulty": q.get("difficulty", "basic"),
            "subskill": q.get("subskill", ""),
            "ability_tag": q.get("ability_tag", "calculation"),
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
            a["figure_svg"] = a.get("figure_svg", "")
            a["correct_answer"] = a.get("correct_answer", "")
            a["explanation"] = a.get("explanation", "")
            a["difficulty_label"] = {
                "basic": "基础",
                "medium": "提升",
                "challenge": "综合",
            }.get(a.get("difficulty"), "基础")
            a["detailed_explanation"] = build_detailed_explanation(a)
            continue

        q = get_question_by_id(a["question_id"])
        if q:
            a["question"] = q["question"]
            a["figure_svg"] = q.get("figure_svg", "")
            a["options"] = q["options"]
            a["correct_answer"] = q["answer"]
            a["explanation"] = q.get("explanation", "")
            a["difficulty_label"] = q.get("difficulty_label", "基础")
        a["detailed_explanation"] = build_detailed_explanation(a)

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
        kp_summary[kp]["weak"] = kp_summary[kp]["rate"] < 65 and t >= 2

    # 全局知识点统计
    all_kp_stats = models.get_student_kp_stats(exam["student_id"])
    recommendations = build_recommendations(all_kp_stats)
    exam_diagnosis = build_exam_diagnosis(answers, kp_summary)
    result_rewards = build_result_rewards(exam, answers, kp_summary)
    progress_delta = build_exam_progress_delta(exam)

    return render_template(
        "result.html",
        student=student,
        exam=exam,
        answers=answers,
        kp_summary=kp_summary,
        all_kp_stats=all_kp_stats,
        recommendations=recommendations,
        exam_diagnosis=exam_diagnosis,
        result_rewards=result_rewards,
        progress_delta=progress_delta,
    )


def build_student_summary(kp_stats):
    weak_count = len([item for item in kp_stats if item["status"] == "weak"])
    watch_count = len([item for item in kp_stats if item["status"] == "watch"])
    secure_count = len([item for item in kp_stats if item["status"] == "secure"])
    top_focus = kp_stats[:3]
    return {
        "weak_count": weak_count,
        "watch_count": watch_count,
        "secure_count": secure_count,
        "top_focus": top_focus,
    }


def build_recent_diagnostic_trend(exams):
    diagnostic_exams = [
        exam for exam in exams
        if exam.get("exam_type") == "diagnostic" and exam.get("submitted_at")
    ][:3]
    if not diagnostic_exams:
        return None

    kp_wrong_counts = defaultdict(int)
    ability_wrong_counts = defaultdict(int)
    exam_count = 0

    for exam in diagnostic_exams:
        answers = models.get_exam_answers(exam["id"])
        if not answers:
            continue
        exam_count += 1
        for answer in answers:
            if answer.get("is_correct"):
                continue
            kp_wrong_counts[answer["knowledge_point"]] += 1
            ability_wrong_counts[answer.get("ability_tag", "calculation")] += 1

    if exam_count == 0:
        return None

    repeated_kps = sorted(
        kp_wrong_counts.items(),
        key=lambda item: (-item[1], item[0]),
    )[:3]
    repeated_abilities = sorted(
        ability_wrong_counts.items(),
        key=lambda item: (-item[1], item[0]),
    )[:2]

    ability_labels = {
        "concept": "概念辨析",
        "calculation": "计算步骤",
        "application": "情境应用",
    }

    return {
        "exam_count": exam_count,
        "repeated_kps": [
            {"kp": kp, "wrong_count": count}
            for kp, count in repeated_kps if count > 0
        ],
        "repeated_abilities": [
            {"ability": ability_labels.get(ability, ability), "wrong_count": count}
            for ability, count in repeated_abilities if count > 0
        ],
    }


def build_growth_badges(exams, summary, kp_stats, activity_calendar=None):
    diagnostic_exams = [exam for exam in exams if exam.get("exam_type") == "diagnostic"]
    submitted_diagnostics = [exam for exam in diagnostic_exams if exam.get("submitted_at")]
    passed_training = [exam for exam in exams if exam.get("exam_type") == "training" and exam.get("submitted_at")]

    badges = [
        {
            "icon": "🚀",
            "title": "初次出发",
            "desc": "完成第一次诊断闯关",
            "earned": len(submitted_diagnostics) >= 1,
        },
        {
            "icon": "🔎",
            "title": "连续探索",
            "desc": "累计完成 3 次诊断卷",
            "earned": len(submitted_diagnostics) >= 3,
        },
        {
            "icon": "🌟",
            "title": "稳定掌握",
            "desc": "已有知识点进入“掌握较稳”",
            "earned": (summary or {}).get("secure_count", 0) >= 1,
        },
        {
            "icon": "🧠",
            "title": "训练达人",
            "desc": "完成过补弱训练卷",
            "earned": len(passed_training) >= 1,
        },
        {
            "icon": "🔥",
            "title": "三天连练",
            "desc": "连续挑战达到 3 天",
            "earned": (activity_calendar or {}).get("streak_days", 0) >= 3,
        },
        {
            "icon": "🏅",
            "title": "一周连练",
            "desc": "连续挑战达到 7 天",
            "earned": (activity_calendar or {}).get("streak_days", 0) >= 7,
        },
    ]

    strongest_kp = next((item for item in kp_stats if item.get("status") == "secure"), None)
    if strongest_kp:
        badges.append({
            "icon": "🧩",
            "title": "知识点点亮",
            "desc": f"“{strongest_kp['kp']}”掌握较稳",
            "earned": True,
        })
    return badges


def exam_accuracy(exam):
    total = exam.get("total", 0) or 0
    score = exam.get("score", 0) or 0
    return round(score / total * 100) if total > 0 else 0


def build_engagement_summary(exams):
    submitted = [exam for exam in exams if exam.get("submitted_at")]
    diagnostics = [exam for exam in submitted if exam.get("exam_type") == "diagnostic"]
    trainings = [exam for exam in submitted if exam.get("exam_type") == "training"]
    avg_accuracy = round(sum(exam_accuracy(exam) for exam in submitted) / len(submitted)) if submitted else 0

    latest_delta = None
    if len(diagnostics) >= 2:
        latest = diagnostics[0]
        previous = diagnostics[1]
        latest_delta = exam_accuracy(latest) - exam_accuracy(previous)

    return {
        "submitted_count": len(submitted),
        "diagnostic_count": len(diagnostics),
        "training_count": len(trainings),
        "avg_accuracy": avg_accuracy,
        "latest_delta": latest_delta,
    }


def build_today_mission(student, summary, engagement_summary):
    weak_count = (summary or {}).get("weak_count", 0)
    diagnostic_count = (engagement_summary or {}).get("diagnostic_count", 0)
    training_count = (engagement_summary or {}).get("training_count", 0)

    if diagnostic_count == 0:
        return {
            "title": "完成第一次诊断闯关",
            "desc": "先做一套诊断卷，建立本学期的起点画像。",
            "cta": "开始诊断闯关",
            "href": f"/exam/diagnostic/{student['id']}",
        }

    if weak_count > 0:
        return {
            "title": "优先补弱训练",
            "desc": f"当前有 {weak_count} 个知识点待点亮，先做针对性训练更高效。",
            "cta": "开始补弱训练",
            "href": f"/exam/training/{student['id']}",
        }

    if training_count == 0:
        return {
            "title": "做一轮巩固训练",
            "desc": "诊断表现稳定后，用训练卷巩固解题步骤和速度。",
            "cta": "开始补弱训练",
            "href": f"/exam/training/{student['id']}",
        }

    return {
        "title": "开启下一次诊断",
        "desc": "继续挑战新题，验证这段时间的掌握是否更稳。",
        "cta": "开始诊断闯关",
        "href": f"/exam/diagnostic/{student['id']}",
    }


def build_exam_progress_delta(current_exam):
    student_exams = models.get_student_exams(current_exam["student_id"])
    submitted_same_type = [
        exam for exam in student_exams
        if exam.get("exam_type") == current_exam.get("exam_type")
        and exam.get("submitted_at")
    ]
    if len(submitted_same_type) < 2:
        return None

    current = submitted_same_type[0]
    previous = submitted_same_type[1]
    delta = exam_accuracy(current) - exam_accuracy(previous)
    return {
        "delta": delta,
        "current_accuracy": exam_accuracy(current),
        "previous_accuracy": exam_accuracy(previous),
    }


def build_activity_calendar(exams):
    submitted = [exam for exam in exams if exam.get("submitted_at")]
    day_counts = defaultdict(int)
    for exam in submitted:
        day_key = exam["submitted_at"][:10]
        day_counts[day_key] += 1

    today = datetime.now().date()
    weekday_labels = ["一", "二", "三", "四", "五", "六", "日"]
    recent_days = []
    for offset in range(29, -1, -1):
        day = today - timedelta(days=offset)
        key = day.strftime("%Y-%m-%d")
        count = day_counts.get(key, 0)
        if count == 0:
            intensity = 0
        elif count == 1:
            intensity = 1
        elif count == 2:
            intensity = 2
        else:
            intensity = 3
        recent_days.append({
            "date_key": key,
            "label": f"{day.month}/{day.day}",
            "weekday": weekday_labels[day.weekday()],
            "count": count,
            "active": count > 0,
            "intensity": intensity,
        })

    streak_days = 0
    if day_counts:
        latest_completed = max(datetime.strptime(day, "%Y-%m-%d").date() for day in day_counts.keys())
        cursor = latest_completed
        while day_counts.get(cursor.strftime("%Y-%m-%d"), 0) > 0:
            streak_days += 1
            cursor -= timedelta(days=1)

    return {
        "streak_days": streak_days,
        "recent_days": recent_days,
        "active_days_30": len([item for item in recent_days if item["active"]]),
    }


def build_exam_coverage_rows(questions, syllabus_kps):
    stats_by_kp = defaultdict(lambda: {"total": 0, "basic": 0, "medium": 0, "challenge": 0})
    for question in questions:
        stats = stats_by_kp[question["kp"]]
        stats["total"] += 1
        stats[question.get("difficulty", "basic")] += 1

    rows = []
    for kp in syllabus_kps:
        stats = stats_by_kp[kp]
        rows.append({
            "kp": kp,
            "total": stats["total"],
            "basic": stats["basic"],
            "medium": stats["medium"],
            "challenge": stats["challenge"],
        })
    return rows


def build_recommendations(kp_stats):
    priority = [item for item in kp_stats if item["status"] != "secure"][:3]
    recommendations = []
    for item in priority:
        recommendations.append({
            "kp": item["kp"],
            "status": item["status"],
            "status_label": item["status_label"],
            "mastery_score": item["mastery_score"],
            "tip": ABILITY_RECOMMENDATIONS.get(item["weak_ability_tag"], "先回到同类基础题，确认核心方法。"),
            "subskill": item.get("weak_subskill") or "同类基础题",
            "evidence_label": item["evidence_label"],
        })
    return recommendations


def build_exam_diagnosis(answers, kp_summary):
    if not answers:
        return []

    wrong_answers = [answer for answer in answers if not answer.get("is_correct")]
    if not wrong_answers:
        return ["本次作答未出现错题，当前这份试卷覆盖范围内的知识点掌握较稳。"]

    weakest = sorted(
        kp_summary.items(),
        key=lambda item: (item[1]["rate"], -item[1]["total"], item[0]),
    )[:3]
    weakest_kps = "、".join(item[0] for item in weakest if item[1]["total"] > 0)

    ability_counts = defaultdict(int)
    difficulty_counts = defaultdict(int)
    for answer in wrong_answers:
        ability_counts[answer.get("ability_tag", "calculation")] += 1
        difficulty_counts[answer.get("difficulty", "basic")] += 1

    dominant_ability = max(
        ability_counts.items(),
        key=lambda item: (item[1], item[0]),
    )[0]
    dominant_difficulty = max(
        difficulty_counts.items(),
        key=lambda item: (item[1], item[0]),
    )[0]

    ability_text = {
        "concept": "概念辨析",
        "calculation": "计算步骤",
        "application": "情境应用",
    }.get(dominant_ability, "基础作答")
    difficulty_text = {
        "basic": "基础题",
        "medium": "提升题",
        "challenge": "综合题",
    }.get(dominant_difficulty, "当前题型")

    diagnosis = []
    if weakest_kps:
        diagnosis.append(f"本次失分主要集中在：{weakest_kps}。")
    diagnosis.append(f"错题更集中出现在“{ability_text}”能力上，建议优先做同类题型的专项回练。")
    diagnosis.append(f"从难度分布看，当前更需要先稳住“{difficulty_text}”的正确率，再逐步加大综合题训练。")
    return diagnosis


def build_result_rewards(exam, answers, kp_summary):
    total = exam.get("total", 0) or 0
    score = exam.get("score", 0) or 0
    accuracy = round(score / total * 100) if total > 0 else 0
    wrong_count = max(total - score, 0)
    weak_kp_count = len([kp for kp, data in kp_summary.items() if data.get("weak")])

    rewards = [
        {
            "icon": "🎯",
            "title": "挑战完成",
            "desc": f"本次共完成 {total} 题",
            "tone": "warm",
        }
    ]
    if wrong_count == 0:
        rewards.append({
            "icon": "👑",
            "title": "全对表现",
            "desc": "本次作答没有出现错题",
            "tone": "good",
        })
    elif accuracy >= 85:
        rewards.append({
            "icon": "🏆",
            "title": "高分徽章",
            "desc": f"正确率达到 {accuracy}%",
            "tone": "good",
        })
    elif accuracy >= 60:
        rewards.append({
            "icon": "⭐",
            "title": "稳步推进",
            "desc": f"正确率达到 {accuracy}%，继续保持",
            "tone": "warm",
        })
    else:
        rewards.append({
            "icon": "🌱",
            "title": "继续升级",
            "desc": f"这次已经找出 {wrong_count} 道待突破题",
            "tone": "alert",
        })

    if weak_kp_count == 0 and total > 0:
        rewards.append({
            "icon": "🎉",
            "title": "本卷点亮",
            "desc": "这份试卷里的知识点表现较稳",
            "tone": "good",
        })
    else:
        rewards.append({
            "icon": "🗺️",
            "title": "下一步目标",
            "desc": f"还有 {weak_kp_count} 个知识点值得优先回练",
            "tone": "alert",
        })
    return rewards


def build_detailed_explanation(answer):
    question = answer.get("question", "").strip()
    knowledge_point = answer.get("knowledge_point", "").strip()
    short_explanation = answer.get("explanation", "").strip()
    correct_answer = format_correct_answer(answer)

    method = KNOWLEDGE_POINT_METHODS.get(
        knowledge_point,
        "先读懂题目条件，判断考查的核心知识，再按对应公式、法则或数量关系一步一步解题。",
    )
    pitfall = KNOWLEDGE_POINT_PITFALLS.get(
        knowledge_point,
        "做完后把结果代回题目检查，看看是否符合题意、单位和数量关系。",
    )
    solving_step = short_explanation or f"根据题目条件逐步推算，可以得到正确答案是 {correct_answer}。"

    lines = [
        f"先审题：这道题考查的是“{knowledge_point}”。做题时先圈出已知条件，再看题目最终要求什么。",
        f"再定方法：{method}",
        f"按步骤解：{solving_step}",
        f"最后检查：看看结果是否和题目中的单位、数量关系以及选项内容一致，本题答案是 {correct_answer}。",
        f"易错提醒：{pitfall}",
    ]
    if question:
        lines.insert(1, f"题目信息：{question}")
    return "\n".join(lines)


def format_correct_answer(answer):
    label = answer.get("correct_answer", "")
    options = answer.get("options") or []
    labels = ["A", "B", "C", "D"]
    if label in labels:
        idx = labels.index(label)
        if idx < len(options):
            return f"{label}（{options[idx]}）"
    return label or "未提供"


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
