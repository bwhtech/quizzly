import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint


class QZQuiz(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		from trivia_tap.triviatap.doctype.qz_question.qz_question import QZQuestion

		default_time_limit: DF.Int
		description: DF.SmallText | None
		questions: DF.Table[QZQuestion]
		title: DF.Data
	# end: auto-generated types

	def validate(self):
		if not self.questions:
			frappe.throw(_("A quiz needs at least one question"))
		for question in self.questions:
			validate_question(question)


def validate_question(question) -> None:
	position = _("Question {0}").format(question.idx)
	if not (question.question_text or "").strip():
		frappe.throw(_("{0} has no text").format(position))
	for index in range(1, 5):
		if not (question.get(f"option_{index}") or "").strip():
			frappe.throw(_("{0}: option {1} is empty").format(position, index))
	if cint(question.correct_option) not in (1, 2, 3, 4):
		frappe.throw(_("{0}: pick which option is correct").format(position))
