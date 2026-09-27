from unittest.mock import patch

import frappe
from frappe.tests import IntegrationTestCase

from trivia_tap.auth import sign_up

EMAIL = "new.host@example.com"
PASSWORD = "Quiz-Host-Pass-2026!"


class TestSignUp(IntegrationTestCase):
	def setUp(self):
		frappe.delete_doc_if_exists("User", EMAIL, force=True)
		frappe.set_user("Guest")
		self.login_manager = patch.object(frappe.local, "login_manager", create=True).start()
		self.signup_disabled = patch("trivia_tap.auth.is_signup_disabled", return_value=False).start()

	def tearDown(self):
		patch.stopall()
		frappe.set_user("Administrator")
		frappe.delete_doc_if_exists("User", EMAIL, force=True)
		super().tearDown()

	def test_creates_a_logged_in_quiz_host(self):
		sign_up("New Host", EMAIL.upper(), PASSWORD)

		user = frappe.get_doc("User", EMAIL)
		self.assertIn("Quiz Host", frappe.get_roles(user.name))
		self.assertEqual(user.first_name, "New Host")
		self.login_manager.login_as.assert_called_once_with(EMAIL)

	def test_refuses_an_existing_email_without_saying_so(self):
		sign_up("New Host", EMAIL, PASSWORD)

		with self.assertRaisesRegex(frappe.ValidationError, "could not create an account"):
			sign_up("Someone Else", EMAIL, PASSWORD)

	def test_refuses_when_sign_up_is_disabled(self):
		self.signup_disabled.return_value = True

		with self.assertRaises(frappe.PermissionError):
			sign_up("New Host", EMAIL, PASSWORD)
		self.assertFalse(frappe.db.exists("User", EMAIL))
