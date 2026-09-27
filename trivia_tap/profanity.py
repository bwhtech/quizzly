"""Nickname profanity check.

ponytail: small curated wordlist with leetspeak folding, matched as a substring.
Substring matching has the Scunthorpe problem (a clean name containing a dirty
run gets rejected); acceptable for 20-character game nicknames. Swap in a real
library if false positives ever get reported.
"""

import re

BLOCKED_WORDS = frozenset(
	{
		"anus",
		"arse",
		"asshole",
		"bastard",
		"bitch",
		"blowjob",
		"boner",
		"clitoris",
		"cock",
		"coon",
		"cunt",
		"dick",
		"dildo",
		"dyke",
		"fag",
		"faggot",
		"fuck",
		"handjob",
		"jizz",
		"kike",
		"nigga",
		"nigger",
		"paki",
		"pedo",
		"penis",
		"piss",
		"porn",
		"pussy",
		"rape",
		"retard",
		"scrotum",
		"semen",
		"shit",
		"slut",
		"spastic",
		"tits",
		"tranny",
		"twat",
		"vagina",
		"wank",
		"whore",
	}
)

LEET_MAP = str.maketrans({"0": "o", "1": "i", "3": "e", "4": "a", "5": "s", "7": "t", "@": "a", "$": "s"})


def is_profane(nickname: str) -> bool:
	folded = re.sub(r"[^a-z]", "", (nickname or "").lower().translate(LEET_MAP))
	return any(word in folded for word in BLOCKED_WORDS)
