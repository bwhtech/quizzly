import frappe

from trivia_tap.avatars import get_boot_pack
from trivia_tap.nicknames import get_boot_words


def get_context(context):
	context.no_cache = 1
	context.boot = {
		"csrf_token": frappe.sessions.get_csrf_token(),
		"site_name": frappe.local.site,
		"session_user": frappe.session.user,
		"avatar_pack": get_boot_pack(),
		"nickname_words": get_boot_words(),
	}
