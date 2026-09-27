import frappe
from frappe.model.document import Document


class QZAnswer(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		is_correct: DF.Check
		participant: DF.Link
		points: DF.Int
		question_row: DF.Data
		response_ms: DF.Int
		selected_option: DF.Literal["1", "2", "3", "4"]
		session: DF.Link
	# end: auto-generated types


def on_doctype_update():
	# Duplicate submits die at the DB level regardless of race conditions
	frappe.db.add_unique("QZ Answer", ["participant", "question_row"])
