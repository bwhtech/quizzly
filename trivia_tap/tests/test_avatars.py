from pathlib import Path

import frappe
from frappe.tests import IntegrationTestCase

from trivia_tap.api import create_session, get_lobby, join_session
from trivia_tap.avatars import default_avatar, get_active_pack, get_boot_pack


class TestAvatars(IntegrationTestCase):
	def setUp(self):
		frappe.set_user("Administrator")
		self.quiz = frappe.get_doc(
			{
				"doctype": "TT Quiz",
				"title": "Avatar Quiz",
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

	def join_as_guest(self, nickname, avatar=None):
		frappe.set_user("Guest")
		try:
			return join_session(self.pin, nickname, avatar)
		finally:
			frappe.set_user("Administrator")

	def test_chosen_avatar_is_stored(self):
		chosen = get_active_pack()["avatars"][3]
		result = self.join_as_guest("alice", chosen)
		self.assertEqual(result["avatar"], chosen)
		self.assertEqual(frappe.db.get_value("TT Participant", result["participant"], "avatar"), chosen)

	def test_unknown_avatar_rejected(self):
		with self.assertRaises(frappe.ValidationError):
			self.join_as_guest("mallory", "not-in-the-pack")

	def test_missing_avatar_falls_back_to_a_stable_pick(self):
		result = self.join_as_guest("bob")
		self.assertEqual(result["avatar"], default_avatar("bob"))
		self.assertIn(result["avatar"], get_active_pack()["avatars"])

	def test_lobby_payload_carries_avatar(self):
		chosen = get_active_pack()["avatars"][1]
		self.join_as_guest("carol", chosen)
		participants = get_lobby(self.session)["participants"]
		self.assertEqual([p["avatar"] for p in participants], [chosen])

	def test_every_avatar_in_the_manifest_is_rendered(self):
		"""Catches a manifest edited without re-running `yarn build:avatars`."""
		app = Path(frappe.get_app_path("trivia_tap"))
		missing = [
			avatar
			for avatar, url in get_active_pack()["urls"].items()
			if not (app / url.replace("/assets/trivia_tap/", "public/", 1)).is_file()
		]
		self.assertEqual(missing, [])

	def test_boot_pack_exposes_id_and_url_per_avatar(self):
		boot = get_boot_pack()
		self.assertEqual(len(boot["avatars"]), len(get_active_pack()["avatars"]))
		self.assertTrue(all(entry["url"].endswith(".svg") for entry in boot["avatars"]))
