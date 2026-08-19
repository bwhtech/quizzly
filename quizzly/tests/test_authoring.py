import frappe
from frappe.client import delete, save
from frappe.tests import IntegrationTestCase

from quizzly import engine
from quizzly.api import create_session, list_quizzes


def question(text="2 + 2?", **overrides) -> dict:
	row = {
		"doctype": "QZ Question",
		"question_text": text,
		"option_1": "3",
		"option_2": "4",
		"option_3": "5",
		"option_4": "6",
		"correct_option": "2",
	}
	row.update(overrides)
	return row


def quiz_doc(questions, base=None) -> dict:
	"""The editor sends back the doc it loaded, with the questions rebuilt in display order."""
	return {**(base or {}), "doctype": "QZ Quiz", "title": "Authored Quiz", "questions": questions}


class TestQuizAuthoring(IntegrationTestCase):
	"""The editor saves through frappe.client.*, so these cover what Quizzly adds to that path:
	the controller's content rules, the question count, and the image on the payload."""

	def setUp(self):
		frappe.set_user("Administrator")

	def test_reorder_survives_a_client_save(self):
		saved = save(quiz_doc([question("First"), question("Second"), question("Third")]))

		reordered = save(quiz_doc([question("Third"), question("First")], base=saved))

		rows = frappe.get_all(
			"QZ Question",
			filters={"parent": reordered["name"]},
			fields=["question_text"],
			order_by="idx asc",
		)
		self.assertEqual([row.question_text for row in rows], ["Third", "First"])

	def test_controller_rejects_broken_quizzes(self):
		with self.assertRaises(frappe.ValidationError):
			save(quiz_doc([]))
		with self.assertRaises(frappe.ValidationError):
			save(quiz_doc([question(option_2="  ")]))
		with self.assertRaises(frappe.ValidationError):
			save(quiz_doc([question(correct_option="7")]))

	def test_list_quizzes_counts_questions(self):
		saved = save(quiz_doc([question("First"), question("Second")]))

		listed = next(quiz for quiz in list_quizzes() if quiz["name"] == saved["name"])

		self.assertEqual(listed["question_count"], 2)

	def test_delete_refuses_while_a_session_references_the_quiz(self):
		saved = save(quiz_doc([question()]))
		create_session(saved["name"])

		with self.assertRaises(frappe.LinkExistsError):
			delete("QZ Quiz", saved["name"])

	def test_image_rides_along_on_the_question_payload(self):
		saved = save(quiz_doc([question(image="/files/cat.png"), question("No picture")]))
		session = frappe.get_doc("QZ Session", create_session(saved["name"])["session"])
		questions = engine.get_quiz_questions(session)

		payloads = [engine.question_payload(session, q, 0, 2, 0.0) for q in questions]

		self.assertEqual(payloads[0]["image_url"], "/files/cat.png")
		self.assertIsNone(payloads[1]["image_url"])

	def test_explainer_survives_a_reorder(self):
		explained = question("Why?", explanation="Because.", explanation_image="/files/why.png")
		saved = save(quiz_doc([question("First"), explained]))

		reordered = save(quiz_doc([explained, question("First")], base=saved))

		rows = frappe.get_all(
			"QZ Question",
			filters={"parent": reordered["name"]},
			fields=["question_text", "explanation", "explanation_image"],
			order_by="idx asc",
		)
		self.assertEqual(rows[0].explanation, "Because.")
		self.assertEqual(rows[0].explanation_image, "/files/why.png")
		self.assertFalse(rows[1].explanation)
