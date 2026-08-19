"""Server-authoritative game loop and hot state for live sessions.

One shared RQ ticker advances every active session's state machine. Clients never tick:
each question payload carries a server-set deadline_ts and clients render
their own countdown. Redis (frappe.cache) is the fast gate for submit
validation; the DB is the durable record.
"""

import time

import frappe
from frappe import _
from frappe.utils import now_datetime, time_diff_in_seconds

GRACE_SECONDS = 1.0
STATS_SECONDS = 5
# a reveal you have to read needs longer than one you only glance at
EXPLAIN_STATS_SECONDS = 12
GETREADY_SECONDS = 3
# ponytail: host gets 5 minutes to hit Next, then the game moves on by itself
ADVANCE_WAIT_CAP = 300
TICK_SECONDS = 0.5
# ponytail: broadcast the live "N answered" counter at most this often, not once per submit
ANSWER_COUNT_THROTTLE = 0.3
STATE_TTL_MARGIN = 30
STREAK_CALLOUT_MIN = 3
ACTIVE_SESSIONS_KEY = "qz:active_sessions"
# ponytail: one shared ticker for all games; 6h covers any single game, re-enqueue on timeout is a Phase 2 scale concern
TICKER_TIMEOUT = 21600


def enqueue_game_loop(session_doc) -> None:
	questions = get_quiz_questions(session_doc)
	if not questions:
		finish_session(session_doc)
		return
	clear_control(session_doc.name)
	get_ready(session_doc, questions[0], 0, len(questions))
	frappe.cache.sadd(ACTIVE_SESSIONS_KEY, session_doc.name)
	frappe.enqueue(
		"quizzly.engine.run_ticker",
		queue="long",
		timeout=TICKER_TIMEOUT,
		job_id="qz_ticker",
		deduplicate=True,
		enqueue_after_commit=True,
	)


def run_ticker() -> None:
	"""One shared self-looping job. Advances every active session on time or host command."""
	# process-local: the ticker is a single deduplicated job, so per-session throttle
	# state and immutable pins live safely in memory for this run.
	answer_count_state: dict = {}
	pin_cache: dict = {}
	while True:
		sessions = active_sessions()
		if not sessions:
			break
		prune_ticker_caches(sessions, answer_count_state, pin_cache)
		for session in sessions:
			frappe.db.savepoint("qz_tick")
			try:
				state = get_state(session)
				if not state:
					frappe.cache.srem(ACTIVE_SESSIONS_KEY, session)
					continue
				control = pop_control(session, ("skip", "advance", "end"))
				if control or time.time() >= state["next_ts"]:
					advance_session(frappe.get_doc("QZ Session", session), state, control)
				else:
					maybe_push_answer_count(session, state, answer_count_state, pin_cache)
				frappe.db.commit()
			except Exception:
				# one bad session must not stall every other live game
				frappe.db.rollback(save_point="qz_tick")
				frappe.log_error(title=f"qz_ticker session {session}")
		time.sleep(TICK_SECONDS)


def maybe_push_answer_count(session: str, state: dict, throttle_state: dict, pin_cache: dict) -> None:
	"""Broadcast the live answered count, but only while a question is open, only on change,
	and at most every ANSWER_COUNT_THROTTLE seconds. Replaces the per-submit broadcast storm."""
	if state["phase"] != "question":
		return
	question_row = state["question_row"]
	count = answered_count(session, question_row)
	prev = throttle_state.get(session)
	now = time.time()
	if prev and prev[0] == question_row:
		if count == prev[1] or now - prev[2] < ANSWER_COUNT_THROTTLE:
			return
	elif count == 0:
		# new question, nobody in yet: host already shows 0 from the question event
		throttle_state[session] = (question_row, 0, now)
		return
	throttle_state[session] = (question_row, count, now)
	pin = pin_cache.get(session)
	if pin is None:
		pin = frappe.db.get_value("QZ Session", session, "game_pin")
		pin_cache[session] = pin
	room = f"qz_session_{pin}"
	frappe.publish_realtime(
		event=room,
		message={"type": "answer_count", "question_row": question_row, "count": count},
		room=room,
	)


def prune_ticker_caches(sessions: list[str], *caches: dict) -> None:
	live = set(sessions)
	for cache in caches:
		for stale in [s for s in cache if s not in live]:
			del cache[stale]


def advance_session(session_doc, state: dict, control: str | None) -> None:
	"""Walk the per-session state machine one step: phase + host control -> next phase."""
	if control == "end":
		finish_session(session_doc)
		return

	phase = state["phase"]
	index = state["q_index"]
	questions = get_quiz_questions(session_doc)
	total = len(questions)
	due = time.time() >= state["next_ts"]

	if phase == "get_ready":
		if due:
			open_question(session_doc, questions[index], index, total)
	elif phase == "question":
		if due or control == "skip":
			close_question(session_doc, questions[index], index, total)
	elif phase == "stats":
		if due or control == "advance":
			if index == total - 1:
				finish_session(session_doc)
			else:
				get_ready(session_doc, questions[index + 1], index + 1, total)


def get_ready(session_doc, question, index: int, total: int) -> None:
	"""Read-the-question pause before the clock starts, Kahoot style."""
	now = time.time()
	deadline_ts = now + GETREADY_SECONDS
	set_state(
		session_doc.name,
		{
			"phase": "get_ready",
			"status": "get_ready",
			"q_index": index,
			"question_row": question.name,
			"opened_at": now,
			"deadline_ts": deadline_ts,
			"next_ts": deadline_ts,
			"window_ms": question_window(question, session_doc) * 1000,
			"total": total,
		},
		ttl=GETREADY_SECONDS + STATE_TTL_MARGIN,
	)
	publish_session_event(
		session_doc,
		{
			"type": "get_ready",
			"q_index": index,
			"total": total,
			"question_text": question.question_text,
			"seconds": GETREADY_SECONDS,
		},
	)


def open_question(session_doc, question, index: int, total: int) -> None:
	window = question_window(question, session_doc)
	opened_at = time.time()
	deadline_ts = opened_at + window
	set_state(
		session_doc.name,
		{
			"phase": "question",
			"status": "question",
			"q_index": index,
			"question_row": question.name,
			"opened_at": opened_at,
			"deadline_ts": deadline_ts,
			"next_ts": deadline_ts + GRACE_SECONDS,
			"window_ms": window * 1000,
			"total": total,
		},
		ttl=window + STATE_TTL_MARGIN,
	)
	frappe.db.set_value("QZ Session", session_doc.name, "current_question", index)
	publish_session_event(session_doc, question_payload(session_doc, question, index, total, deadline_ts))


def close_question(session_doc, question, index: int, total: int) -> None:
	state = get_state(session_doc.name) or {}
	window_ms = state.get("window_ms") or question_window(question, session_doc) * 1000
	options = frappe.db.get_value(
		"QZ Session", session_doc.name, ["auto_advance", "show_explainer"], as_dict=True
	)
	explainer = explainer_payload(question, options.show_explainer)
	stats_seconds = EXPLAIN_STATS_SECONDS if explainer else STATS_SECONDS
	set_state(
		session_doc.name,
		{
			**state,
			"phase": "stats",
			"status": "closed",
			"next_ts": time.time() + (stats_seconds if options.auto_advance else ADVANCE_WAIT_CAP),
		},
		ttl=ADVANCE_WAIT_CAP + STATE_TTL_MARGIN,
	)
	participants = get_live_participants(session_doc.name)
	answers = frappe.get_all(
		"QZ Answer",
		filters={"session": session_doc.name, "question_row": question.name},
		fields=["name", "participant", "selected_option", "response_ms"],
	)
	answer_by_participant = {a.participant: a for a in answers}
	distribution = {"1": 0, "2": 0, "3": 0, "4": 0}
	answer_updates = {}
	participant_updates = {}

	for participant in participants:
		answer = answer_by_participant.get(participant.name)
		if not answer:
			participant.streak = 0
			participant_updates[participant.name] = {"streak": 0}
			continue
		distribution[str(answer.selected_option)] += 1
		is_correct = str(answer.selected_option) == str(question.correct_option)
		if is_correct:
			participant.streak += 1
			points = compute_points(
				answer.response_ms, window_ms, participant.streak, int(question.points_multiplier or 1)
			)
		else:
			participant.streak = 0
			points = 0
		participant.score += points
		answer_updates[answer.name] = {"is_correct": int(is_correct), "points": points}
		participant_updates[participant.name] = {"score": participant.score, "streak": participant.streak}

	frappe.db.bulk_update("QZ Answer", answer_updates)
	frappe.db.bulk_update("QZ Participant", participant_updates)

	top_5 = [
		{"nickname": p.nickname, "avatar": p.avatar, "score": p.score}
		for p in sorted(participants, key=lambda p: -p.score)[:5]
	]
	streaks = [
		{"nickname": p.nickname, "avatar": p.avatar, "streak": p.streak}
		for p in sorted(participants, key=lambda p: -p.streak)
		if p.streak >= STREAK_CALLOUT_MIN
	][:3]
	publish_session_event(
		session_doc,
		{
			"type": "question_closed",
			"q_index": index,
			"total": total,
			"question_row": question.name,
			"correct_option": question.correct_option,
			"distribution": distribution,
			"top_5": top_5,
			"streaks": streaks,
			"is_last": index == total - 1,
			**explainer,
		},
	)
	frappe.cache.delete_value(answered_key(session_doc.name, question.name))
	frappe.db.commit()


def active_sessions() -> list[str]:
	members = frappe.cache.smembers(ACTIVE_SESSIONS_KEY)
	return [m.decode() if isinstance(m, bytes) else m for m in members]


def is_loop_alive(session: str) -> bool:
	"""Every loop phase re-sets state with a TTL that outlives that phase, so no state = no loop."""
	return get_state(session) is not None


def is_abandoned(session_doc) -> bool:
	"""Active but nothing is driving it: the worker died or was restarted mid-game.

	The age check covers the gap between start_session and the loop's first state write.
	"""
	if session_doc.status != "Active" or is_loop_alive(session_doc.name):
		return False
	last_touched = session_doc.started_at or session_doc.modified
	return time_diff_in_seconds(now_datetime(), last_touched) > STATE_TTL_MARGIN


def end_active_session(session_doc) -> None:
	"""Ask the loop to stop. With no loop left to read the flag, end it here instead."""
	if is_loop_alive(session_doc.name):
		set_control(session_doc.name, "end")
	else:
		finish_session(session_doc)


def finish_session(session_doc) -> None:
	status = frappe.db.get_value("QZ Session", session_doc.name, "status", for_update=True)
	if status in ("Ended", "Cancelled"):
		return
	participants = get_live_participants(session_doc.name)
	participants.sort(key=lambda p: (-p.score, p.joined_at or now_datetime()))
	leaderboard = []
	rank_updates = {}
	for rank, participant in enumerate(participants, start=1):
		rank_updates[participant.name] = {"rank": rank}
		leaderboard.append(
			{
				"nickname": participant.nickname,
				"avatar": participant.avatar,
				"score": participant.score,
				"rank": rank,
			}
		)
	frappe.db.bulk_update("QZ Participant", rank_updates)
	frappe.db.set_value(
		"QZ Session",
		session_doc.name,
		{"status": "Ended", "ended_at": now_datetime()},
	)
	publish_session_event(
		session_doc,
		{"type": "podium", "top_3": leaderboard[:3], "leaderboard": leaderboard},
	)
	clear_state(session_doc.name)
	frappe.cache.srem(ACTIVE_SESSIONS_KEY, session_doc.name)
	frappe.db.commit()


def compute_points(response_ms: int, window_ms: int, streak: int, multiplier: int) -> int:
	"""Kahoot formula. `streak` is the participant's streak including this answer."""
	response_ms = min(max(response_ms or 0, 0), window_ms)
	base = round((1 - (response_ms / window_ms) / 2) * 1000)
	bonus = min(streak - 1, 5) * 50
	return (base + bonus) * multiplier


def state_key(session: str) -> str:
	return f"qz:{session}:state"


def answered_key(session: str, question_row: str) -> str:
	return f"qz:{session}:answered:{question_row}"


def control_key(session: str) -> str:
	return f"qz:{session}:control"


def set_state(session: str, state: dict, ttl: float) -> None:
	frappe.cache.set_value(state_key(session), state, expires_in_sec=int(ttl))


def get_state(session: str) -> dict | None:
	# never from process-local cache: the long-lived ticker must see state that
	# expired or was written by another process, or it spins on a vanished session
	return frappe.cache.get_value(state_key(session), use_local_cache=False)


def clear_state(session: str) -> None:
	frappe.cache.delete_value(state_key(session))
	frappe.cache.delete_value(control_key(session))


def set_control(session: str, command: str) -> None:
	frappe.cache.set_value(control_key(session), command, expires_in_sec=ADVANCE_WAIT_CAP)


def pop_control(session: str, accepted: tuple) -> str | None:
	control = frappe.cache.get_value(control_key(session), use_local_cache=False)
	if control in accepted:
		frappe.cache.delete_value(control_key(session))
		return control
	return None


def clear_control(session: str) -> None:
	frappe.cache.delete_value(control_key(session))


def mark_answered(session: str, question_row: str, participant: str, ttl: float) -> bool:
	"""Fast duplicate pre-check. Returns False if this participant already answered."""
	if has_answered(session, question_row, participant):
		return False
	key = answered_key(session, question_row)
	frappe.cache.sadd(key, participant)
	frappe.cache.expire(frappe.cache.make_key(key), int(ttl))
	return True


def has_answered(session: str, question_row: str, participant: str) -> bool:
	return bool(frappe.cache.sismember(answered_key(session, question_row), participant))


def answered_count(session: str, question_row: str) -> int:
	return len(frappe.cache.smembers(answered_key(session, question_row)))


def question_payload(session_doc, question, index: int, total: int, deadline_ts: float) -> dict:
	"""Hand-built payload: correct_option must never ride along."""
	return {
		"type": "question",
		"q_index": index,
		"total": total,
		"question_row": question.name,
		"question_text": question.question_text,
		"image_url": question.image or None,
		"options": [question.option_1, question.option_2, question.option_3, question.option_4],
		"deadline_ts": deadline_ts,
		# clients count down from this instead of deadline_ts, so client clock skew cannot matter
		"window_ms": question_window(question, session_doc) * 1000,
		"randomize_answer_order": int(session_doc.randomize_answer_order or 0),
		"points_multiplier": int(question.points_multiplier or 1),
	}


def explainer_payload(question, show_explainer) -> dict:
	"""Empty unless the session wants an explainer and the question carries one.

	Kept out of every pre-close payload on purpose: an explanation gives the answer away.
	"""
	if not show_explainer or not (question.explanation or question.explanation_image):
		return {}
	return {
		"explanation": question.explanation or None,
		"explanation_image": question.explanation_image or None,
	}


def question_window(question, session_doc) -> int:
	return question.time_limit or get_quiz(session_doc).default_time_limit or 20


def get_quiz(session_doc):
	return frappe.get_cached_doc("QZ Quiz", session_doc.quiz)


def get_quiz_questions(session_doc):
	return get_quiz(session_doc).questions


def get_live_participants(session: str) -> list:
	return frappe.get_all(
		"QZ Participant",
		filters={"session": session, "kicked": 0},
		fields=["name", "nickname", "avatar", "score", "streak", "joined_at"],
	)


def publish_session_event(session_doc, message: dict) -> None:
	room = f"qz_session_{session_doc.game_pin}"
	frappe.publish_realtime(event=room, message=message, room=room, after_commit=True)
