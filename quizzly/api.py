import hashlib
import secrets
import time

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import now_datetime, strip_html_tags

from quizzly import engine
from quizzly.engine import publish_session_event
from quizzly.profanity import is_profane

NICKNAME_MAX_LENGTH = 20


@frappe.whitelist()
def create_session(quiz: str) -> dict:
	quiz_doc = frappe.get_doc("QZ Quiz", quiz)
	quiz_doc.check_permission("read")
	session = frappe.get_doc(
		{
			"doctype": "QZ Session",
			"quiz": quiz_doc.name,
			"host": frappe.session.user,
			"game_pin": generate_game_pin(),
			"status": "Lobby",
		}
	).insert()
	return {"session": session.name, "game_pin": session.game_pin}


@frappe.whitelist()
def lock_lobby(session: str) -> dict:
	return set_lobby_locked(session, True)


@frappe.whitelist()
def unlock_lobby(session: str) -> dict:
	return set_lobby_locked(session, False)


@frappe.whitelist()
def kick_participant(session: str, participant: str) -> None:
	session_doc = get_host_session(session)
	participant_doc = frappe.get_doc("QZ Participant", participant)
	if participant_doc.session != session_doc.name:
		frappe.throw(_("Participant does not belong to this session"))
	participant_doc.kicked = 1
	participant_doc.save(ignore_permissions=True)
	publish_session_event(session_doc, {"type": "kicked", "participant": participant_doc.name})
	publish_lobby_update(session_doc)


@frappe.whitelist()
def get_lobby(session: str) -> dict:
	session_doc = get_host_session(session)
	return get_lobby_state(session_doc)


@frappe.whitelist()
def get_host_state(session: str | None = None) -> dict:
	"""Whole host screen in one call, for first paint and for reload mid-game."""
	session_doc = get_host_session(session) if session else get_live_host_session()
	if not session_doc or session_doc.status == "Cancelled":
		return {}
	if engine.is_abandoned(session_doc):
		# the host reloaded into a game whose worker is gone: settle it and show the podium
		engine.finish_session(session_doc)
		session_doc.reload()
	quiz = engine.get_quiz(session_doc)
	result = {
		"session": session_doc.name,
		"game_pin": session_doc.game_pin,
		"quiz_title": quiz.title,
		"auto_advance": session_doc.auto_advance,
		"show_host_controls": quiz.show_host_controls,
		**get_lobby_state(session_doc),
	}
	if session_doc.status == "Lobby":
		return result

	state = engine.get_state(session_doc.name)
	if not state:
		result["leaderboard"] = get_leaderboard(session_doc.name)
		return result

	question = get_question_row(session_doc, state["question_row"])
	answers = frappe.get_all(
		"QZ Answer",
		filters={"session": session_doc.name, "question_row": question.name},
		fields=["selected_option"],
	)
	result.update(
		{
			"phase": state["status"],
			"remaining_seconds": max(0.0, state["deadline_ts"] - time.time()),
			"answer_count": len(answers),
			"question": {
				**engine.question_payload(
					session_doc, question, state["q_index"], state["total"], state["deadline_ts"]
				),
				"correct_option": question.correct_option,
			},
		}
	)
	if state["status"] == "explanation":
		result["explanation"] = state["explanation"]
	if state["status"] == "closed":
		distribution = {"1": 0, "2": 0, "3": 0, "4": 0}
		for answer in answers:
			distribution[str(answer.selected_option)] += 1
		result["distribution"] = distribution
		result["explanation_next"] = bool(state.get("explanation_after"))
	if state["status"] == "scoreboard":
		result["scoreboard"] = state["scoreboard"]
	return result


@frappe.whitelist()
def start_session(session: str) -> dict:
	session_doc = get_host_session(session)
	if session_doc.status != "Lobby":
		frappe.throw(_("Session has already started"))
	if not frappe.db.exists("QZ Participant", {"session": session_doc.name, "kicked": 0}):
		frappe.throw(_("No participants have joined yet"))
	session_doc.status = "Active"
	session_doc.started_at = now_datetime()
	session_doc.save()
	engine.enqueue_game_loop(session_doc)
	publish_session_event(session_doc, {"type": "session_started"})
	return {"ok": True}


@frappe.whitelist()
def set_auto_advance(session: str, enabled: int) -> dict:
	session_doc = get_host_session(session)
	session_doc.db_set("auto_advance", int(enabled))
	return {"auto_advance": session_doc.auto_advance}


@frappe.whitelist()
def next_question(session: str) -> dict:
	engine.set_control(get_host_session(session).name, "advance")
	return {"ok": True}


@frappe.whitelist()
def skip_question(session: str) -> dict:
	engine.set_control(get_host_session(session).name, "skip")
	return {"ok": True}


@frappe.whitelist()
def end_session(session: str) -> dict:
	session_doc = get_host_session(session)
	if session_doc.status == "Lobby":
		session_doc.status = "Cancelled"
		session_doc.ended_at = now_datetime()
		session_doc.save()
		publish_session_event(session_doc, {"type": "session_ended"})
	elif session_doc.status == "Active":
		engine.end_active_session(session_doc)
	return {"ok": True}


@frappe.whitelist()
def list_quizzes() -> list[dict]:
	quizzes = frappe.get_list("QZ Quiz", fields=["name", "title"], order_by="modified desc")
	for quiz in quizzes:
		# ponytail: one count per quiz; group them if a host ever owns hundreds
		quiz["question_count"] = frappe.db.count("QZ Question", {"parent": quiz.name})
	return quizzes


# Guests join by design (no login); rate-limited, PIN-gated, and input is sanitized below.
# nosemgrep: frappe-semgrep-rules.rules.security.guest-whitelisted-method
@frappe.whitelist(allow_guest=True, methods=["POST"])
def join_session(pin: str, nickname: str, avatar: str | None = None) -> dict:
	session = get_session_by_pin(pin)
	if session.status != "Lobby":
		frappe.throw(_("Game has already started"))
	if session.lobby_locked:
		frappe.throw(_("Lobby is locked"))

	nickname = strip_html_tags(nickname or "").strip()[:NICKNAME_MAX_LENGTH]
	if is_profane(nickname):
		frappe.throw(_("Pick a nickname everyone can see on the big screen"))
	if frappe.db.exists("QZ Participant", {"session": session.name, "nickname": nickname, "kicked": 0}):
		frappe.throw(_("That nickname is taken, pick another"), frappe.DuplicateEntryError)

	token = secrets.token_hex(32)
	participant = frappe.get_doc(
		{
			"doctype": "QZ Participant",
			"session": session.name,
			"nickname": nickname,
			"avatar": avatar,
			"token_hash": hash_token(token),
			"joined_at": now_datetime(),
		}
	).insert(ignore_permissions=True)
	publish_lobby_update(session)
	return {
		"participant_token": token,
		"participant": participant.name,
		"nickname": participant.nickname,
		"avatar": participant.avatar,
		"session": session.name,
		"game_pin": session.game_pin,
		**get_lobby_state(session),
	}


@frappe.whitelist(allow_guest=True, methods=["POST"])
def submit_answer(pin: str, token: str, question_row: str, selected_option: str) -> dict:
	received_at = time.time()
	session = get_session_by_pin(pin)
	if session.status != "Active":
		frappe.throw(_("Game is not active"))
	participant = get_participant_by_token(session, token)

	state = engine.get_state(session.name)
	if not state or state.get("status") != "question" or state.get("question_row") != question_row:
		frappe.throw(_("This question is not open"))
	if received_at > state["deadline_ts"] + engine.GRACE_SECONDS:
		frappe.throw(_("Too late, the question is closed"))
	if str(selected_option) not in ("1", "2", "3", "4"):
		frappe.throw(_("Invalid option"))

	if not engine.mark_answered(
		session.name, question_row, participant.name, ttl=state["window_ms"] / 1000 + 300
	):
		frappe.throw(_("Already answered"))
	try:
		frappe.get_doc(
			{
				"doctype": "QZ Answer",
				"session": session.name,
				"participant": participant.name,
				"question_row": question_row,
				"selected_option": str(selected_option),
				"response_ms": int((received_at - state["opened_at"]) * 1000),
			}
		).insert(ignore_permissions=True, ignore_links=True)
	except frappe.UniqueValidationError:
		frappe.throw(_("Already answered"))
	# the live answered count is now broadcast by the ticker (throttled), not per-submit
	return {"ok": True}


# Players are guests by design; the participant token gates every read below.
# nosemgrep: frappe-semgrep-rules.rules.security.guest-whitelisted-method
@frappe.whitelist(allow_guest=True)
def get_state(pin: str, token: str) -> dict:
	session = get_session_by_pin(pin)
	participant = get_participant_by_token(session, token)
	result = {
		"status": session.status,
		"nickname": participant.nickname,
		"avatar": participant.avatar,
		"score": participant.score,
		"streak": participant.streak,
		"rank": get_rank(session.name, participant),
	}
	if session.status == "Lobby":
		return {**result, **get_lobby_state(session)}
	if session.status == "Ended":
		return {**result, "leaderboard": get_leaderboard(session.name)}

	state = engine.get_state(session.name)
	if not state:
		return result
	question = get_question_row(session, state["question_row"])
	result.update(
		{
			"phase": state["status"],
			"q_index": state["q_index"],
			"total": state["total"],
			"deadline_ts": state["deadline_ts"],
			"remaining_seconds": max(0.0, state["deadline_ts"] - time.time()),
			"answered": engine.has_answered(session.name, state["question_row"], participant.name),
			"question": engine.question_payload(
				session, question, state["q_index"], state["total"], state["deadline_ts"]
			),
		}
	)
	if state["status"] == "explanation":
		result["explanation"] = state["explanation"]
	return result


@frappe.whitelist(allow_guest=True)
def get_result(pin: str, token: str, question_row: str) -> dict:
	"""Own outcome for the result interstitial; the broadcast stays free of per-player data."""
	session = get_session_by_pin(pin)
	participant = get_participant_by_token(session, token)
	answer = frappe.db.get_value(
		"QZ Answer",
		{"session": session.name, "participant": participant.name, "question_row": question_row},
		["is_correct", "points", "selected_option"],
		as_dict=True,
	)
	return {
		"answered": bool(answer),
		"is_correct": bool(answer and answer.is_correct),
		"points": (answer and answer.points) or 0,
		"selected_option": answer and answer.selected_option,
		"score": participant.score,
		"streak": participant.streak,
		"rank": get_rank(session.name, participant),
		"top_5": get_leaderboard(session.name)[:5],
	}


@frappe.whitelist(allow_guest=True, methods=["POST"])
def leave_session(pin: str, token: str) -> None:
	session = get_session_by_pin(pin)
	participant = get_participant_by_token(session, token)
	# ponytail: leave only matters in the lobby; mid-game the row must survive for scores
	if session.status == "Lobby":
		frappe.delete_doc("QZ Participant", participant.name, ignore_permissions=True, force=True)
		publish_lobby_update(session)


def get_host_session(session: str) -> Document:
	doc = frappe.get_doc("QZ Session", session)
	if doc.host != frappe.session.user:
		frappe.throw(_("You are not the host of this session"), frappe.PermissionError)
	return doc


def get_live_host_session() -> Document | None:
	names = frappe.get_all(
		"QZ Session",
		filters={"host": frappe.session.user, "status": ("in", ("Lobby", "Active"))},
		pluck="name",
		order_by="creation desc",
	)
	for name in names:
		doc = frappe.get_doc("QZ Session", name)
		# games left Active by a dead worker would otherwise hide the quiz picker forever
		if engine.is_abandoned(doc):
			engine.finish_session(doc)
			continue
		return doc
	return None


def get_session_by_pin(pin: str) -> Document:
	pin = (pin or "").strip()
	# Ended is allowed so a player who reloads on the podium still gets it back
	name = pin and frappe.db.get_value(
		"QZ Session", {"game_pin": pin, "status": ("in", ("Lobby", "Active", "Ended"))}
	)
	if not name:
		frappe.throw(_("Invalid game PIN"), frappe.DoesNotExistError)
	return frappe.get_doc("QZ Session", name)


def get_participant_by_token(session: Document, token: str) -> Document:
	name = frappe.db.get_value(
		"QZ Participant",
		{"session": session.name, "token_hash": hash_token(token or ""), "kicked": 0},
	)
	if not name:
		frappe.throw(_("Not a participant of this session"), frappe.PermissionError)
	return frappe.get_doc("QZ Participant", name)


def get_leaderboard(session: str) -> list[dict]:
	participants = engine.get_live_participants(session)
	participants.sort(key=lambda p: -p.score)
	return [
		{"nickname": p.nickname, "avatar": p.avatar, "score": p.score, "rank": rank}
		for rank, p in enumerate(participants, start=1)
	]


def get_rank(session: str, participant: Document) -> int:
	ahead = frappe.db.count(
		"QZ Participant", {"session": session, "kicked": 0, "score": (">", participant.score)}
	)
	return ahead + 1


def get_lobby_state(session: Document) -> dict:
	participants = frappe.get_all(
		"QZ Participant",
		filters={"session": session.name, "kicked": 0},
		fields=["name", "nickname", "avatar"],
		order_by="joined_at asc",
	)
	return {
		"status": session.status,
		"lobby_locked": session.lobby_locked,
		"participants": participants,
	}


def set_lobby_locked(session: str, locked: bool) -> dict:
	doc = get_host_session(session)
	doc.lobby_locked = int(locked)
	doc.save()
	publish_lobby_update(doc)
	return get_lobby_state(doc)


def publish_lobby_update(session: Document) -> None:
	publish_session_event(session, {"type": "lobby_update", **get_lobby_state(session)})


def get_question_row(session: Document, question_row: str) -> Document:
	for question in engine.get_quiz_questions(session):
		if question.name == question_row:
			return question
	frappe.throw(_("Question not found"))


def hash_token(token: str) -> str:
	return hashlib.sha256(token.encode()).hexdigest()


def generate_game_pin() -> str:
	# ponytail: pins stay unique forever (DB unique column); revisit if sessions ever near 1M
	for _attempt in range(20):
		pin = f"{secrets.randbelow(1_000_000):06d}"
		if not frappe.db.exists("QZ Session", {"game_pin": pin}):
			return pin
	frappe.throw(_("Could not allocate a game PIN, please retry"))
