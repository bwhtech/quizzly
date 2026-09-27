from frappe.model.document import Document


class QZSession(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		auto_advance: DF.Check
		current_question: DF.Int
		ended_at: DF.Datetime | None
		game_pin: DF.Data | None
		host: DF.Link
		lobby_locked: DF.Check
		quiz: DF.Link
		randomize_answer_order: DF.Check
		started_at: DF.Datetime | None
		status: DF.Literal["Lobby", "Active", "Ended", "Cancelled"]
	# end: auto-generated types
