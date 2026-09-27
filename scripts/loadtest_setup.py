# Load-test setup. Runs in frappe context so it can mint participants without the
# single-IP join throttle (an artifact of driving from one host, not the system).
# It also arms the game (Active + first get_ready) so a foreground run_ticker can
# drive it deterministically, instead of depending on the dev bench's single RQ
# worker actually scheduling the shared ticker in time.
#   bench --site trivia-tap.localhost console < scripts/loadtest_setup.py
# Writes pin + tokens to /tmp/trivia_tap_loadtest.json for scripts/loadtest.py to drive.

import json
import os
import secrets
from pathlib import Path

import frappe

from trivia_tap import api, engine

QUIZ_TITLE = "General Knowledge"
PLAYERS = int(os.environ.get("TT_LOADTEST_PLAYERS", "100"))
STATE_FILE = Path("/tmp/trivia_tap_loadtest.json")

quiz = frappe.db.get_value("TT Quiz", {"title": QUIZ_TITLE}, "name")
assert quiz, f"seed {QUIZ_TITLE!r} first (scripts/seed_demo.py)"

frappe.set_user("Administrator")
created = api.create_session(quiz)
session_name, pin = created["session"], created["game_pin"]

tokens = []
for i in range(PLAYERS):
	token = secrets.token_hex(32)
	frappe.get_doc(
		{
			"doctype": "TT Participant",
			"session": session_name,
			"nickname": f"bot{i:02d}",
			"token_hash": api.hash_token(token),
			"joined_at": frappe.utils.now_datetime(),
		}
	).insert(ignore_permissions=True)
	tokens.append(token)

session = frappe.get_doc("TT Session", session_name)
session.status = "Active"
session.started_at = frappe.utils.now_datetime()
session.auto_advance = 1
session.save(ignore_permissions=True)

questions = engine.get_quiz_questions(session)
engine.clear_control(session_name)
engine.get_ready(session, questions[0], 0, len(questions))
frappe.cache.sadd(engine.ACTIVE_SESSIONS_KEY, session_name)
frappe.db.commit()

STATE_FILE.write_text(json.dumps({"pin": pin, "session": session_name, "tokens": tokens}))
print(f"armed session={session_name} pin={pin} players={PLAYERS} questions={len(questions)}")
