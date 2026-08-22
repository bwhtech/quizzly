from frappe import _


def get_data():
	return {
		"fieldname": "session",
		"transactions": [{"label": _("Gameplay"), "items": ["QZ Participant", "QZ Answer"]}],
	}
