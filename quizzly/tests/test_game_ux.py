import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import add_to_date, now_datetime

from quizzly import engine
from quizzly.api import (
	end_session,
	get_host_state,
	get_result,
	get_state,
	join_session,
	set_session_option,
	submit_answer,
)
from quizzly.profanity import is_profane
from quizzly.tests.test_engine import GameTestCase


class TestProfanityFilter(IntegrationTestCase):
	def test_clean_nicknames_pass(self):
		for nickname in ("Alice", "xX_Dragon_Xx", "Scott", "assassin_42", "Class1"):
			self.assertFalse(is_profane(nickname), nickname)

	def test_dirty_nicknames_blocked(self):
		for nickname in ("fuck", "Sh1tLord", "b i t c h", "@sshole", "n1gger"):
			self.assertTrue(is_profane(nickname), nickname)


class TestJoinFiltersNicknames(GameTestCase):
	def test_profane_nickname_rejected_with_message(self):
		with self.assertRaises(frappe.ValidationError) as caught:
			join_session(self.pin, "fuckface")
		self.assertIn("nickname", str(caught.exception).lower())


class TestHostState(GameTestCase):
	def test_lobby_state(self):
		state = get_host_state(self.session)
		self.assertEqual(state["game_pin"], self.pin)
		self.assertEqual(state["status"], "Lobby")
		self.assertEqual(len(state["participants"]), 2)

	def test_finds_live_session_without_argument(self):
		self.assertEqual(get_host_state()["session"], self.session)

	def test_mid_question_state_carries_correct_option_for_host(self):
		self.activate()
		question = self.open_question(window=30)
		submit_answer(self.pin, self.alice["participant_token"], question.name, "2")

		state = get_host_state(self.session)
		self.assertEqual(state["phase"], "question")
		self.assertEqual(state["answer_count"], 1)
		self.assertGreater(state["remaining_seconds"], 25)
		self.assertEqual(state["question"]["correct_option"], question.correct_option)

	def test_non_host_is_refused(self):
		frappe.set_user("Guest")
		with self.assertRaises(frappe.PermissionError):
			get_host_state(self.session)


class TestPlayerResult(GameTestCase):
	def test_result_reports_own_outcome_and_rank(self):
		self.activate()
		question = self.open_question(window=30)
		submit_answer(self.pin, self.alice["participant_token"], question.name, "2")
		engine.close_question(self.session_doc, question, 0, len(self.questions))

		result = get_result(self.pin, self.alice["participant_token"], question.name)
		self.assertTrue(result["is_correct"])
		self.assertGreater(result["points"], 0)
		self.assertEqual(result["rank"], 1)
		self.assertEqual(result["top_5"][0]["nickname"], "alice")

		missed = get_result(self.pin, self.bob["participant_token"], question.name)
		self.assertFalse(missed["answered"])
		self.assertEqual(missed["points"], 0)
		self.assertEqual(missed["rank"], 2)

	def test_podium_survives_reload_after_the_game_ends(self):
		frappe.db.set_value("QZ Session", self.session, "status", "Ended")
		state = get_state(self.pin, self.alice["participant_token"])
		self.assertEqual(state["status"], "Ended")
		self.assertEqual(len(state["leaderboard"]), 2)


class TestExplainerOnReconnect(GameTestCase):
	def setUp(self):
		super().setUp()
		self.activate()
		quiz = frappe.get_doc("QZ Quiz", self.quiz.name)
		quiz.questions[0].explanation = "Because 2 + 2 = 4."
		quiz.questions[0].explanation_image = "/files/why.png"
		quiz.save()
		self.questions = quiz.questions
		self.question = self.open_question(window=30)
		submit_answer(self.pin, self.alice["participant_token"], self.question.name, "2")
		engine.close_question(self.session_doc, self.questions[0], 0, len(self.questions))

	def test_host_reload_mid_reveal_keeps_the_explainer(self):
		state = get_host_state(self.session)
		self.assertEqual(state["phase"], "closed")
		self.assertEqual(state["explanation"], "Because 2 + 2 = 4.")
		self.assertEqual(state["explanation_image"], "/files/why.png")

	def test_player_result_carries_the_explainer(self):
		result = get_result(self.pin, self.alice["participant_token"], self.question.name)
		self.assertEqual(result["explanation"], "Because 2 + 2 = 4.")
		self.assertEqual(result["explanation_image"], "/files/why.png")

	def test_toggle_off_hides_it_from_both_reconnect_paths(self):
		set_session_option(self.session, "show_explainer", 0)
		self.assertNotIn("explanation", get_host_state(self.session))
		self.assertNotIn(
			"explanation", get_result(self.pin, self.alice["participant_token"], self.question.name)
		)


class TestSessionOptions(GameTestCase):
	def test_each_option_is_writable(self):
		for option in ("auto_advance", "randomize_answer_order", "show_explainer"):
			self.assertEqual(set_session_option(self.session, option, 0), {option: 0})
			self.assertEqual(frappe.db.get_value("QZ Session", self.session, option), 0)

	def test_unknown_option_is_refused(self):
		with self.assertRaises(frappe.ValidationError):
			set_session_option(self.session, "status", 0)
		self.assertEqual(frappe.db.get_value("QZ Session", self.session, "status"), "Lobby")

	def test_non_host_is_refused(self):
		frappe.set_user("Guest")
		with self.assertRaises(frappe.PermissionError):
			set_session_option(self.session, "show_explainer", 0)


class TestAbandonedSession(GameTestCase):
	"""A worker restart mid-game leaves an Active session nobody is driving."""

	def abandon(self, seconds_ago=120):
		self.activate()
		engine.clear_state(self.session)
		frappe.db.set_value(
			"QZ Session", self.session, "started_at", add_to_date(now_datetime(), seconds=-seconds_ago)
		)
		self.session_doc.reload()

	def test_host_state_reaps_it_and_offers_a_fresh_game(self):
		self.abandon()
		self.assertEqual(get_host_state(), {})
		self.assertEqual(frappe.db.get_value("QZ Session", self.session, "status"), "Ended")

	def test_running_game_is_left_alone(self):
		self.activate()
		frappe.db.set_value("QZ Session", self.session, "started_at", now_datetime())
		self.open_question()
		self.assertEqual(get_host_state()["session"], self.session)
		self.assertEqual(frappe.db.get_value("QZ Session", self.session, "status"), "Active")

	def test_just_started_game_is_not_reaped_before_the_loop_writes_state(self):
		self.activate()
		engine.clear_state(self.session)
		frappe.db.set_value("QZ Session", self.session, "started_at", now_datetime())
		self.session_doc.reload()
		self.assertEqual(get_host_state()["session"], self.session)

	def test_lobby_waiting_for_players_is_never_reaped(self):
		frappe.db.set_value("QZ Session", self.session, "modified", add_to_date(now_datetime(), seconds=-600))
		self.session_doc.reload()
		self.assertEqual(get_host_state()["session"], self.session)
		self.assertEqual(frappe.db.get_value("QZ Session", self.session, "status"), "Lobby")

	def test_end_session_ends_it_instead_of_flagging_a_dead_loop(self):
		self.abandon()
		end_session(self.session)
		self.assertEqual(frappe.db.get_value("QZ Session", self.session, "status"), "Ended")

	def test_remembered_session_settles_to_a_podium(self):
		self.abandon()
		state = get_host_state(self.session)
		self.assertEqual(state["status"], "Ended")
		self.assertEqual(len(state["leaderboard"]), 2)
