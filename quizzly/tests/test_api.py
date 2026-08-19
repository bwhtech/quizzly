import frappe
from frappe.tests import IntegrationTestCase

from quizzly.api import (
	create_session,
	join_session,
	kick_participant,
	leave_session,
	lock_lobby,
	unlock_lobby,
)


class TestLobbyFlow(IntegrationTestCase):
	def setUp(self):
		frappe.set_user("Administrator")
		self.quiz = frappe.get_doc(
			{
				"doctype": "QZ Quiz",
				"title": "Test Quiz",
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
		created = create_session(self.quiz.name)
		self.session = created["session"]
		self.pin = created["game_pin"]

	def tearDown(self):
		frappe.set_user("Administrator")
		super().tearDown()

	def join_as_guest(self, nickname="alice", pin=None):
		frappe.set_user("Guest")
		try:
			return join_session(pin or self.pin, nickname)
		finally:
			frappe.set_user("Administrator")

	def test_session_created_with_pin(self):
		session = frappe.get_doc("QZ Session", self.session)
		self.assertEqual(session.status, "Lobby")
		self.assertEqual(session.host, "Administrator")
		self.assertRegex(session.game_pin, r"^\d{6}$")

	def test_join_returns_token_and_lobby_snapshot(self):
		result = self.join_as_guest("alice")
		self.assertEqual(len(result["participant_token"]), 64)
		self.assertEqual(result["nickname"], "alice")
		self.assertEqual([p.nickname for p in result["participants"]], ["alice"])
		stored = frappe.db.get_value("QZ Participant", result["participant"], "token_hash")
		self.assertNotEqual(stored, result["participant_token"])

	def test_wrong_pin_rejected(self):
		wrong_pin = "000000" if self.pin != "000000" else "000001"
		with self.assertRaises(frappe.DoesNotExistError):
			self.join_as_guest(pin=wrong_pin)

	def test_duplicate_nickname_rejected(self):
		self.join_as_guest("alice")
		with self.assertRaises(frappe.DuplicateEntryError):
			self.join_as_guest("alice")

	def test_locked_lobby_rejects_join_until_unlocked(self):
		lock_lobby(self.session)
		with self.assertRaises(frappe.ValidationError):
			self.join_as_guest("bob")
		unlock_lobby(self.session)
		self.join_as_guest("bob")

	def test_kick_frees_nickname_and_rejects_token(self):
		joined = self.join_as_guest("mallory")
		kick_participant(self.session, joined["participant"])
		self.join_as_guest("mallory")
		frappe.set_user("Guest")
		try:
			with self.assertRaises(frappe.PermissionError):
				leave_session(self.pin, joined["participant_token"])
		finally:
			frappe.set_user("Administrator")

	def test_leave_removes_participant(self):
		joined = self.join_as_guest("carol")
		frappe.set_user("Guest")
		try:
			leave_session(self.pin, joined["participant_token"])
		finally:
			frappe.set_user("Administrator")
		self.assertFalse(frappe.db.exists("QZ Participant", joined["participant"]))

	def test_non_host_cannot_control_session(self):
		frappe.set_user("Guest")
		try:
			with self.assertRaises(frappe.PermissionError):
				lock_lobby(self.session)
		finally:
			frappe.set_user("Administrator")


class TestHostDataIsolation(IntegrationTestCase):
	def setUp(self):
		frappe.set_user("Administrator")
		self.other_host = make_quiz_host("other-host@quizzly.test")
		quiz = frappe.get_doc(
			{
				"doctype": "QZ Quiz",
				"title": "Isolation Quiz",
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
		created = create_session(quiz.name)
		self.session = created["session"]
		frappe.set_user("Guest")
		try:
			join_session(created["game_pin"], "Player")
		finally:
			frappe.set_user("Administrator")

	def tearDown(self):
		frappe.set_user("Administrator")
		super().tearDown()

	def test_host_cannot_list_other_hosts_participants(self):
		frappe.set_user(self.other_host)
		try:
			visible = frappe.get_list("QZ Participant", pluck="name")
			self.assertEqual(visible, [], "a host must not see another host's participants")
			with self.assertRaises(frappe.PermissionError):
				frappe.get_doc(
					"QZ Participant",
					frappe.db.get_value("QZ Participant", {"session": self.session}, "name"),
				).check_permission("read")
		finally:
			frappe.set_user("Administrator")


def make_quiz_host(email: str) -> str:
	if not frappe.db.exists("User", email):
		user = frappe.get_doc(
			{"doctype": "User", "email": email, "first_name": "Host", "send_welcome_email": 0}
		).insert(ignore_permissions=True)
		user.add_roles("Quiz Host")
	return email
