"""Curated words for the join-screen nickname suggestions.

The list lives here rather than in the SPA so the profanity test can prove the
whole cross product is clean: the filter matches substrings, so two harmless
words can still form a blocked one across the join.
"""

ADJECTIVES = (
	"Swift",
	"Brave",
	"Clever",
	"Sunny",
	"Lucky",
	"Bold",
	"Cosmic",
	"Neon",
	"Turbo",
	"Mighty",
	"Quiet",
	"Jolly",
	"Rapid",
	"Golden",
	"Silver",
	"Wild",
	"Nimble",
	"Bright",
	"Fuzzy",
	"Zesty",
)

NOUNS = (
	"Falcon",
	"Otter",
	"Comet",
	"Panda",
	"Tiger",
	"Maple",
	"Rocket",
	"Puffin",
	"Cactus",
	"Dragon",
	"Walrus",
	"Marble",
	"Pixel",
	"Mango",
	"Badger",
	"Meteor",
	"Quokka",
	"Lantern",
	"Narwhal",
	"Pepper",
)


def get_boot_words() -> dict:
	return {"adjectives": list(ADJECTIVES), "nouns": list(NOUNS)}
