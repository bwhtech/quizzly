import frappe
from frappe import _
from frappe.core.doctype.user.user import get_signup_limit, update_password
from frappe.rate_limiter import rate_limit
from frappe.utils import cint, escape_html
from frappe.website.utils import is_signup_disabled


# Frappe's own sign_up only mails a password link; a host wants to write a quiz
# right away, so this one takes the password and logs them in.
# nosemgrep: frappe-semgrep-rules.rules.security.guest-whitelisted-method
@frappe.whitelist(allow_guest=True, methods=["POST"])
@rate_limit(limit=get_signup_limit, seconds=60)
def sign_up(full_name: str, email: str, password: str) -> None:
	if is_signup_disabled():
		frappe.throw(_("Sign up is disabled on this site."), frappe.PermissionError)
	if signups_past_hour_exceeded():
		frappe.throw(_("Too many sign ups right now. Try again in an hour."), frappe.RateLimitExceededError)
	# same wording as frappe, so the form cannot tell which emails have accounts
	if frappe.db.exists("User", {"email": email.strip().lower()}):
		frappe.throw(_("We could not create an account with the provided details."))

	user = frappe.get_doc(
		{
			"doctype": "User",
			"email": email,
			"first_name": escape_html(full_name.strip()),
			"new_password": password,
			"send_welcome_email": 0,
			"roles": [{"role": "Quiz Host"}],
		}
	)
	user.flags.ignore_permissions = True
	user.insert()
	frappe.local.login_manager.login_as(user.name)


@frappe.whitelist(methods=["POST"])
@rate_limit(limit=10, seconds=10 * 60)
def change_password(old_password: str, new_password: str) -> None:
	# frappe clears the session cookies on an AuthenticationError, so a typo in the
	# current password would log the host out of the page they are on
	try:
		frappe.local.login_manager.check_password(frappe.session.user, old_password)
	except frappe.AuthenticationError:
		frappe.throw(_("Current password is wrong."))
	update_password(new_password, old_password=old_password)


def signups_past_hour_exceeded() -> bool:
	limit = cint(frappe.get_system_settings("max_signups_allowed_per_hour") or 300)
	return frappe.db.get_creation_count("User", 60) >= limit
