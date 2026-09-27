from frappe.model.document import Document


class QZQuestion(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		correct_option: DF.Literal["1", "2", "3", "4"]
		image: DF.AttachImage | None
		option_1: DF.Data
		option_2: DF.Data
		option_3: DF.Data
		option_4: DF.Data
		parent: DF.Data
		parentfield: DF.Data
		parenttype: DF.Data
		points_multiplier: DF.Literal["0", "1", "2"]
		question_text: DF.SmallText
		time_limit: DF.Int
	# end: auto-generated types
