"""Avatar packs.

A pack is a JSON manifest in `avatar_packs/`, listing the roster the picker
shows and the server validates against. The active pack comes from
`site_config.trivia_tap_avatar_pack`. Swapping art, editing the roster, or adding
avatars is a manifest change, never a code change.
"""

import json
import zlib
from functools import cache
from pathlib import Path

import frappe
from frappe import _

DEFAULT_PACK = "notionists"
PACKS_DIR = Path(__file__).parent / "avatar_packs"


def get_active_pack() -> dict:
	return load_pack(frappe.conf.get("trivia_tap_avatar_pack") or DEFAULT_PACK)


@cache
def load_pack(pack_id: str) -> dict:
	manifest = PACKS_DIR / f"{pack_id}.json"
	if not manifest.is_file():
		frappe.throw(_("Unknown avatar pack {0}").format(pack_id))

	pack = json.loads(manifest.read_text())
	extension = pack.get("extension", "svg")
	pack["urls"] = {
		avatar: f"/assets/trivia_tap/avatars/{pack['id']}/{avatar}.{extension}" for avatar in pack["avatars"]
	}
	return pack


def is_valid_avatar(avatar: str) -> bool:
	return avatar in get_active_pack()["urls"]


def default_avatar(nickname: str) -> str:
	"""Stable pick for clients that send no avatar, so nobody renders blank."""
	roster = get_active_pack()["avatars"]
	return roster[zlib.crc32(nickname.encode()) % len(roster)]


def get_boot_pack() -> dict:
	"""Pack payload for the SPA, injected into the portal page boot context."""
	pack = get_active_pack()
	return {
		"id": pack["id"],
		"name": pack["name"],
		"attribution": pack.get("attribution"),
		"avatars": [{"id": avatar, "url": url} for avatar, url in pack["urls"].items()],
	}
