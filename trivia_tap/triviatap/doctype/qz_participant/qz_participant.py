import frappe
from frappe import _
from frappe.model.document import Document

from trivia_tap.avatars import default_avatar, is_valid_avatar


class QZParticipant(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		avatar: DF.Data | None
		joined_at: DF.Datetime | None
		kicked: DF.Check
		nickname: DF.Data
		rank: DF.Int
		score: DF.Int
		session: DF.Link
		streak: DF.Int
		token_hash: DF.Data | None
	# end: auto-generated types

	def validate(self):
		self.nickname = self.nickname.strip()
		if not self.nickname:
			frappe.throw(_("Nickname is required"))
		self.validate_avatar()
		# ponytail: exists-check has a race window; a duplicate slipping through is cosmetic
		duplicate = frappe.db.exists(
			"QZ Participant",
			{
				"session": self.session,
				"nickname": self.nickname,
				"kicked": 0,
				"name": ("!=", self.name),
			},
		)
		if duplicate:
			frappe.throw(_("Nickname is already taken"), frappe.DuplicateEntryError)

	def validate_avatar(self):
		if not self.avatar:
			self.avatar = default_avatar(self.nickname)
		elif not is_valid_avatar(self.avatar):
			# Rejected rather than defaulted: a silent fallback hides a stale
			# client or a manifest edited without re-running build:avatars.
			frappe.throw(_("Unknown avatar {0}").format(self.avatar))
