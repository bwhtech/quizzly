# Demo content for README screenshots. Throwaway: run it, take the pictures.
# Usage: bench --site trivia-tap.localhost console < scripts/seed_demo.py

import frappe

TITLE = "General Knowledge"

QUESTIONS = [
	{
		"question_text": "Which planet in our solar system has the most moons?",
		"option_1": "Jupiter",
		"option_2": "Saturn",
		"option_3": "Neptune",
		"option_4": "Uranus",
		"correct_option": "2",
	},
	{
		"question_text": "What is the capital city of Australia?",
		"option_1": "Sydney",
		"option_2": "Melbourne",
		"option_3": "Canberra",
		"option_4": "Perth",
		"correct_option": "3",
	},
	{
		"question_text": "Which element has the chemical symbol 'Au'?",
		"option_1": "Silver",
		"option_2": "Aluminium",
		"option_3": "Argon",
		"option_4": "Gold",
		"correct_option": "4",
	},
	{
		"question_text": "Who painted 'The Starry Night'?",
		"option_1": "Vincent van Gogh",
		"option_2": "Claude Monet",
		"option_3": "Pablo Picasso",
		"option_4": "Salvador Dali",
		"correct_option": "1",
	},
	{
		"question_text": "How many strings does a standard violin have?",
		"option_1": "Six",
		"option_2": "Five",
		"option_3": "Four",
		"option_4": "Seven",
		"correct_option": "3",
	},
]

frappe.db.delete("TT Quiz", {"title": TITLE})

# nosemgrep: frappe-semgrep-rules.rules.frappe-breaks-multitenancy
quiz = frappe.get_doc(
	{
		"doctype": "TT Quiz",
		"title": TITLE,
		"description": "A five-question warm-up round. Fast fingers win.",
		"default_time_limit": 20,
		"questions": QUESTIONS,
	}
).insert()

# bench console never commits on exit
frappe.db.commit()  # nosemgrep
print("seeded", quiz.name)
