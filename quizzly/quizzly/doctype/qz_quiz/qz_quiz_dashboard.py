from frappe import _


def get_data():
	return {
		"fieldname": "quiz",
		"transactions": [{"label": _("Gameplay"), "items": ["QZ Session"]}],
	}
