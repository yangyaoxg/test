import os
import tempfile
import unittest

import app
import models
import questions


def question_signature(question):
    text = " ".join((question.get("question") or "").split())
    options = tuple(" ".join(option.split()) for option in (question.get("options") or []))
    return text, options


class MathQuizAppTestCase(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.original_db_path = models.DB_PATH
        self.original_questions = [dict(q) for q in questions.QUESTIONS]

        models.DB_PATH = os.path.join(self.temp_dir.name, "test_math_quiz.db")
        models.init_db()

        app.app.config["TESTING"] = True
        self.client = app.app.test_client()

    def tearDown(self):
        questions.QUESTIONS[:] = self.original_questions
        models.DB_PATH = self.original_db_path
        self.temp_dir.cleanup()

    def create_student(self, name="测试学生", grade="四年级下学期"):
        response = self.client.post(
            "/student/create",
            data={"name": name, "grade": grade},
            follow_redirects=False,
        )
        self.assertEqual(response.status_code, 302)
        students = models.get_all_students()
        self.assertEqual(len(students), 1)
        return students[0]

    def create_exam_and_submit(self, student_id, answer_overrides=None):
        answer_overrides = answer_overrides or {}
        response = self.client.get(f"/exam/diagnostic/{student_id}")
        self.assertEqual(response.status_code, 200)

        exams = models.get_student_exams(student_id)
        self.assertEqual(len(exams), 1)
        exam = exams[0]

        payload = {"exam_id": str(exam["id"])}
        for qid in models.get_exam(exam["id"])["question_ids"]:
            question = questions.get_question_by_id(qid)
            payload[f"q_{qid}"] = answer_overrides.get(qid, question["answer"])

        submit_response = self.client.post(
            "/exam/submit",
            data=payload,
            follow_redirects=False,
        )
        self.assertEqual(submit_response.status_code, 302)
        return exam["id"]

    def test_duplicate_submission_does_not_create_duplicate_answers(self):
        student = self.create_student()
        exam_id = self.create_exam_and_submit(student["id"])

        exam = models.get_exam(exam_id)
        question_ids = exam["question_ids"]
        first_answers = models.get_exam_answers(exam_id)
        first_stats = models.get_student_kp_stats(student["id"])

        self.assertEqual(len(first_answers), len(question_ids))
        self.assertIsNotNone(exam["submitted_at"])

        payload = {"exam_id": str(exam_id)}
        for qid in question_ids:
            payload[f"q_{qid}"] = questions.get_question_by_id(qid)["answer"]

        second_submit = self.client.post("/exam/submit", data=payload, follow_redirects=False)
        self.assertEqual(second_submit.status_code, 302)

        second_answers = models.get_exam_answers(exam_id)
        second_stats = models.get_student_kp_stats(student["id"])

        self.assertEqual(len(second_answers), len(first_answers))
        self.assertEqual(second_stats, first_stats)

    def test_result_page_uses_persisted_question_snapshot(self):
        student = self.create_student()
        exam_id = self.create_exam_and_submit(student["id"])

        exam_answers = models.get_exam_answers(exam_id)
        self.assertTrue(exam_answers)
        original_snapshot = exam_answers[0]["question_text"]
        self.assertTrue(original_snapshot)

        question_id = exam_answers[0]["question_id"]
        for question in questions.QUESTIONS:
            if question["id"] == question_id:
                question["question"] = "已被修改的新题干"
                question["options"] = ["新A", "新B", "新C", "新D"]
                question["answer"] = "D"
                question["explanation"] = "新的解析"
                break

        response = self.client.get(f"/exam/result/{exam_id}")
        self.assertEqual(response.status_code, 200)
        page = response.get_data(as_text=True)

        self.assertIn(original_snapshot, page)
        self.assertNotIn("已被修改的新题干", page)

    def test_result_page_shows_detailed_solution_steps(self):
        student = self.create_student()
        exam_id = self.create_exam_and_submit(student["id"])

        response = self.client.get(f"/exam/result/{exam_id}")
        self.assertEqual(response.status_code, 200)
        page = response.get_data(as_text=True)

        self.assertIn("先审题：这道题考查的是", page)
        self.assertIn("再定方法：", page)
        self.assertIn("按步骤解：", page)
        self.assertIn("易错提醒：", page)
        self.assertIn("本次诊断结论", page)

    def test_result_page_shows_exam_diagnosis_for_wrong_answers(self):
        student = self.create_student()
        response = self.client.get(f"/exam/diagnostic/{student['id']}")
        self.assertEqual(response.status_code, 200)

        exams = models.get_student_exams(student["id"])
        exam = exams[0]
        payload = {"exam_id": str(exam["id"])}

        question_ids = models.get_exam(exam["id"])["question_ids"]
        for index, qid in enumerate(question_ids):
            question = questions.get_question_by_id(qid)
            payload[f"q_{qid}"] = "Z" if index < 8 else question["answer"]

        submit_response = self.client.post("/exam/submit", data=payload, follow_redirects=False)
        self.assertEqual(submit_response.status_code, 302)

        result_response = self.client.get(f"/exam/result/{exam['id']}")
        self.assertEqual(result_response.status_code, 200)
        page = result_response.get_data(as_text=True)

        self.assertIn("本次诊断结论", page)
        self.assertIn("本次失分主要集中在：", page)
        self.assertIn("建议优先做同类题型的专项回练", page)

    def test_exam_and_result_pages_render_svg_figures(self):
        student = self.create_student(grade="五年级上学期")
        response = self.client.get(f"/exam/diagnostic/{student['id']}")
        self.assertEqual(response.status_code, 200)
        exam_page = response.get_data(as_text=True)
        self.assertIn("<svg", exam_page)
        self.assertIn("question-figure", exam_page)
        exam = models.get_student_exams(student["id"])[0]
        selected_questions = [
            questions.get_question_by_id(qid)
            for qid in models.get_exam(exam["id"])["question_ids"]
        ]
        self.assertGreaterEqual(
            sum(1 for question in selected_questions if question.get("figure_svg")),
            3,
        )

        payload = {"exam_id": str(exam["id"])}
        for qid in models.get_exam(exam["id"])["question_ids"]:
            question = questions.get_question_by_id(qid)
            payload[f"q_{qid}"] = question["answer"]
        submit_response = self.client.post("/exam/submit", data=payload, follow_redirects=False)
        self.assertEqual(submit_response.status_code, 302)

        result_response = self.client.get(f"/exam/result/{exam['id']}")
        self.assertEqual(result_response.status_code, 200)
        result_page = result_response.get_data(as_text=True)
        self.assertIn("<svg", result_page)
        self.assertIn("question-figure", result_page)

    def test_each_grade_has_enough_questions_for_diagnostic_exam(self):
        for grade in questions.GRADE_OPTIONS:
            grade_questions = questions.get_questions_for_grade(grade)
            syllabus_kps = questions.get_syllabus_knowledge_points(grade)
            self.assertGreaterEqual(len(grade_questions), questions.EXAM_TARGETS["diagnostic"] * 4)
            self.assertTrue(syllabus_kps)
            for knowledge_point in questions.get_knowledge_points(grade):
                self.assertGreaterEqual(len(questions.get_questions_by_kp(grade, knowledge_point)), 30)
            diagnostic_questions = questions.build_diagnostic_questions(grade)
            self.assertEqual(len(diagnostic_questions), questions.EXAM_TARGETS["diagnostic"])
            self.assertTrue(all(question.get("difficulty") for question in diagnostic_questions))
            self.assertTrue(all(question.get("ability_tag") for question in diagnostic_questions))
            self.assertTrue(all(question["grade"] == grade for question in diagnostic_questions))
            self.assertEqual(
                len({question_signature(question) for question in diagnostic_questions}),
                len(diagnostic_questions),
            )
            figure_count = sum(1 for question in diagnostic_questions if question.get("figure_svg"))
            self.assertGreaterEqual(figure_count, 3)
            self.assertLessEqual(figure_count, 5)

            second_diagnostic = questions.build_diagnostic_questions(
                grade,
                excluded_ids=[question["id"] for question in diagnostic_questions],
            )
            self.assertEqual(len(second_diagnostic), questions.EXAM_TARGETS["diagnostic"])
            self.assertFalse(
                {question["id"] for question in diagnostic_questions}
                & {question["id"] for question in second_diagnostic}
            )

    def test_create_student_with_semester_grade(self):
        student = self.create_student(grade="三年级上学期")
        self.assertEqual(student["grade"], "三年级上学期")

        detail_response = self.client.get(f"/student/{student['id']}")
        self.assertEqual(detail_response.status_code, 200)
        detail_page = detail_response.get_data(as_text=True)
        self.assertIn("本学期知识点", detail_page)
        self.assertIn("混合运算", detail_page)
        self.assertIn("认识小数", detail_page)

        response = self.client.get(f"/exam/diagnostic/{student['id']}")
        self.assertEqual(response.status_code, 200)
        page = response.get_data(as_text=True)
        self.assertIn("本学期教材知识点共", page)
        self.assertIn("本卷实际抽到的知识点", page)
        self.assertIn("抽题分布", page)
        self.assertIn("基础", page)
        self.assertIn("提升", page)
        self.assertIn("综合", page)
        self.assertIn("混合运算", page)

    def test_student_page_shows_recent_diagnostic_trend(self):
        student = self.create_student(grade="五年级下学期")

        for wrong_count in (6, 5, 4):
            response = self.client.get(f"/exam/diagnostic/{student['id']}")
            self.assertEqual(response.status_code, 200)
            exam = models.get_student_exams(student["id"])[0]
            payload = {"exam_id": str(exam["id"])}
            question_ids = models.get_exam(exam["id"])["question_ids"]
            for index, qid in enumerate(question_ids):
                question = questions.get_question_by_id(qid)
                payload[f"q_{qid}"] = "Z" if index < wrong_count else question["answer"]
            submit_response = self.client.post("/exam/submit", data=payload, follow_redirects=False)
            self.assertEqual(submit_response.status_code, 302)

        detail_response = self.client.get(f"/student/{student['id']}")
        self.assertEqual(detail_response.status_code, 200)
        detail_page = detail_response.get_data(as_text=True)

        self.assertIn("最近 3 次诊断卷趋势", detail_page)
        self.assertIn("已纳入 3 次已提交的诊断卷", detail_page)
        self.assertIn("累计错题", detail_page)

    def test_repeated_diagnostic_exam_avoids_reusing_identical_question_set(self):
        student = self.create_student(grade="五年级下学期")

        first_response = self.client.get(f"/exam/diagnostic/{student['id']}")
        self.assertEqual(first_response.status_code, 200)
        first_exam = models.get_student_exams(student["id"])[0]
        first_ids = models.get_exam(first_exam["id"])["question_ids"]

        second_response = self.client.get(f"/exam/diagnostic/{student['id']}")
        self.assertEqual(second_response.status_code, 200)
        exams = models.get_student_exams(student["id"])
        self.assertEqual(len(exams), 2)
        second_exam = exams[0]
        second_ids = models.get_exam(second_exam["id"])["question_ids"]

        self.assertEqual(len(first_ids), questions.EXAM_TARGETS["diagnostic"])
        self.assertEqual(len(second_ids), questions.EXAM_TARGETS["diagnostic"])
        self.assertNotEqual(set(first_ids), set(second_ids))
        self.assertFalse(set(first_ids) & set(second_ids))

    def test_low_sample_size_is_not_marked_as_weak(self):
        student = self.create_student()
        exam_id = self.create_exam_and_submit(student["id"])
        exam = models.get_exam(exam_id)
        answers = models.get_exam_answers(exam_id)
        target_kp = answers[0]["knowledge_point"]

        conn = models.get_db()
        conn.execute("DELETE FROM answers WHERE exam_id = ?", (exam_id,))
        conn.execute("UPDATE exams SET score = 0 WHERE id = ?", (exam_id,))
        kept = 0
        for answer in answers:
            if answer["knowledge_point"] != target_kp or kept >= 2:
                continue
            conn.execute(
                """INSERT INTO answers (
                       exam_id, question_id, student_answer, is_correct, knowledge_point,
                       question_text, options_json, correct_answer, explanation,
                       difficulty, subskill, ability_tag
                   ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    exam_id,
                    answer["question_id"],
                    "Z",
                    0,
                    answer["knowledge_point"],
                    answer["question_text"],
                    answer["options_json"],
                    answer["correct_answer"],
                    answer["explanation"],
                    answer["difficulty"],
                    answer["subskill"],
                    answer["ability_tag"],
                ),
            )
            kept += 1
        conn.commit()
        conn.close()

        kp_stats = models.get_student_kp_stats(student["id"])
        stat = next(item for item in kp_stats if item["kp"] == target_kp)

        self.assertEqual(stat["total"], 2)
        self.assertEqual(stat["status"], "watch")
        self.assertEqual(stat["status_label"], "证据不足")


if __name__ == "__main__":
    unittest.main()
