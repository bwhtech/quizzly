import frappe


def execute():
	for name in frappe.get_all("TT Quiz", filters={"name": ("like", "QZ-%")}, pluck="name"):
		frappe.rename_doc("TT Quiz", name, "TT-" + name.removeprefix("QZ-"), force=True)
