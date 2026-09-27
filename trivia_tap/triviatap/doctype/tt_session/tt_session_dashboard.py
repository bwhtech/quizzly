from frappe import _


def get_data():
	return {
		"fieldname": "session",
		"transactions": [{"label": _("Gameplay"), "items": ["TT Participant", "TT Answer"]}],
	}
