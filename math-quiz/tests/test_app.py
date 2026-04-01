import os
import tempfile
import unittest

import app
import models
import questions


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

    def test_each_grade_has_enough_questions_for_diagnostic_exam(self):
        for grade in questions.GRADE_OPTIONS:
            grade_questions = questions.get_questions_for_grade(grade)
            self.assertGreaterEqual(len(grade_questions), 40)
            for knowledge_point in questions.get_knowledge_points(grade):
                self.assertTrue(questions.get_questions_by_kp(grade, knowledge_point))

    def test_create_student_with_semester_grade(self):
        student = self.create_student(grade="三年级上学期")
        self.assertEqual(student["grade"], "三年级上学期")

        response = self.client.get(f"/exam/diagnostic/{student['id']}")
        self.assertEqual(response.status_code, 200)


if __name__ == "__main__":
    unittest.main()
