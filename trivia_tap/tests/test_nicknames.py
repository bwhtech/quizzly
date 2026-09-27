from frappe.tests import IntegrationTestCase

from trivia_tap.nicknames import ADJECTIVES, NOUNS, get_boot_words
from trivia_tap.profanity import is_profane


class TestNicknameWords(IntegrationTestCase):
	def test_no_generated_nickname_is_profane(self):
		"""The filter matches substrings, so a clean pair can still join into a dirty word."""
		dirty = [
			f"{adjective}{noun}"
			for adjective in ADJECTIVES
			for noun in NOUNS
			if is_profane(f"{adjective}{noun}")
		]
		self.assertEqual(dirty, [])

	def test_generated_nicknames_fit_the_input_limit(self):
		longest = max(len(a) + len(n) for a in ADJECTIVES for n in NOUNS)
		self.assertLessEqual(longest, 20)

	def test_boot_words_expose_both_lists(self):
		words = get_boot_words()
		self.assertEqual(words["adjectives"], list(ADJECTIVES))
		self.assertEqual(words["nouns"], list(NOUNS))
