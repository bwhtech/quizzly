import frappe


def execute():
	for name in ("Quiz", "Question", "Session", "Participant", "Answer"):
		old_name, new_name = f"QZ {name}", f"TT {name}"
		if frappe.db.exists("DocType", old_name) and not frappe.db.exists("DocType", new_name):
			frappe.rename_doc("DocType", old_name, new_name, force=True)
