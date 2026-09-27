import frappe
from frappe.tests import IntegrationTestCase

from trivia_tap.api import create_session, join_session

HOST = "perm.host@example.com"
OTHER_HOST = "perm.other@example.com"


class TestHostSeesOnlyTheirGames(IntegrationTestCase):
	def setUp(self):
		frappe.set_user("Administrator")
		for email in (HOST, OTHER_HOST):
			frappe.delete_doc_if_exists("User", email, force=True)
			frappe.get_doc(
				{"doctype": "User", "email": email, "first_name": "Host", "roles": [{"role": "Quiz Host"}]}
			).insert()

		frappe.set_user(HOST)
		quiz = frappe.get_doc(
			{
				"doctype": "TT Quiz",
				"title": "Private quiz",
				"questions": [
					{
						"question_text": "2 + 2?",
						"option_1": "3",
						"option_2": "4",
						"option_3": "5",
						"option_4": "6",
						"correct_option": "2",
					}
				],
			}
		).insert()
		self.quiz = quiz.name
		self.session = create_session(quiz.name)
		frappe.set_user("Guest")
		self.participant = join_session(self.session["game_pin"], "Kid")["participant"]
		self.answer = (
			frappe.get_doc(
				{
					"doctype": "TT Answer",
					"session": self.session["session"],
					"participant": self.participant,
					"question_row": "1",
					"selected_option": "2",
				}
			)
			.insert(ignore_permissions=True)
			.name
		)

	def tearDown(self):
		frappe.set_user("Administrator")
		frappe.db.rollback()
		super().tearDown()

	def test_host_sees_their_players_and_answers(self):
		frappe.set_user(HOST)

		self.assertIn(self.participant, frappe.get_list("TT Participant", pluck="name"))
		self.assertIn(self.answer, frappe.get_list("TT Answer", pluck="name"))
		self.assertTrue(frappe.has_permission("TT Participant", doc=self.participant))

	def test_other_host_sees_none_of_it(self):
		frappe.set_user(OTHER_HOST)

		self.assertNotIn(self.quiz, frappe.get_list("TT Quiz", pluck="name"))
		self.assertNotIn(self.participant, frappe.get_list("TT Participant", pluck="name"))
		self.assertNotIn(self.answer, frappe.get_list("TT Answer", pluck="name"))
		self.assertFalse(frappe.has_permission("TT Quiz", doc=self.quiz))
		self.assertFalse(frappe.has_permission("TT Session", doc=self.session["session"]))
		self.assertFalse(frappe.has_permission("TT Participant", doc=self.participant))
		self.assertFalse(frappe.has_permission("TT Answer", doc=self.answer))
