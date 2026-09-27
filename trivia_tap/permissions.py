import frappe

# Players and answers are created by guests, so an if_owner rule cannot scope them.
# A host sees them through the session they host.


def session_host_query(user: str | None = None, doctype: str | None = None) -> str:
	user = user or frappe.session.user
	if is_system_manager(user):
		return ""
	return (
		f"`tab{doctype}`.session in "
		f"(select name from `tabTT Session` where host = {frappe.db.escape(user)})"
	)


def is_session_host(doc, user: str | None = None) -> bool:
	user = user or frappe.session.user
	if is_system_manager(user):
		return True
	return frappe.db.get_value("TT Session", doc.session, "host") == user


def is_system_manager(user: str) -> bool:
	return "System Manager" in frappe.get_roles(user)
