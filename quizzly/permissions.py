import frappe


def session_scoped_conditions(user: str | None, doctype: str) -> str:
	"""List filter: a host sees only rows whose session they host.

	QZ Participant and QZ Answer grant Quiz Host a role-wide read and own no
	`owner` of their own, so ownership is inherited from the linked session's host.
	"""
	user = user or frappe.session.user
	if "System Manager" in frappe.get_roles(user):
		return ""
	owned_sessions = f"select name from `tabQZ Session` where host = {frappe.db.escape(user)}"
	return f"`tab{doctype}`.`session` in ({owned_sessions})"


def participant_query_conditions(user: str | None = None) -> str:
	return session_scoped_conditions(user, "QZ Participant")


def answer_query_conditions(user: str | None = None) -> str:
	return session_scoped_conditions(user, "QZ Answer")


def owns_session_row(doc, ptype=None, user: str | None = None) -> bool:
	"""has_permission hook: a host may only reach rows of sessions they host.

	Reached only after role perms already grant read, so a plain ownership test
	is enough to narrow that role-wide grant to the host's own sessions.
	"""
	user = user or frappe.session.user
	if "System Manager" in frappe.get_roles(user):
		return True
	return frappe.db.get_value("QZ Session", doc.session, "host") == user
