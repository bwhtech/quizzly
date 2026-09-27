# Fills a live session with plausible players so the README screenshots show a
# populated lobby, distribution and podium. Throwaway: run it, take the pictures.
#
#   python scripts/demo_bots.py join 123456
#   python scripts/demo_bots.py answer 123456

import json
import random
import sys
import time
from pathlib import Path

import requests

BASE = "http://trivia-tap.localhost:8000/api/method/trivia_tap.api"
STATE_FILE = Path("/tmp/trivia_tap_demo_bots.json")

# (nickname, avatar id, chance of answering correctly)
BOTS = [
	("Priya", "otter", 0.9),
	("Marcus", "fox", 0.75),
	("Aisha", "panda", 0.8),
	("Diego", "tiger", 0.6),
	("Lena", "koala", 0.7),
	("Kwame", "lemur", 0.55),
	("Yuki", "puffin", 0.65),
]


ANSWER_KEY = {
	"Which planet in our solar system has the most moons?": "2",
	"What is the capital city of Australia?": "3",
	"Which element has the chemical symbol 'Au'?": "4",
	"Who painted 'The Starry Night'?": "1",
	"How many strings does a standard violin have?": "3",
}


def call(method, **params):
	response = requests.post(f"{BASE}.{method}", json=params, timeout=10)
	response.raise_for_status()
	return response.json()["message"]


def join(pin):
	players = []
	for nickname, avatar, accuracy in BOTS:
		result = call("join_session", pin=pin, nickname=nickname, avatar=avatar)
		players.append({"nickname": nickname, "token": result["participant_token"], "accuracy": accuracy})
		print("joined", nickname)
		time.sleep(0.4)
	STATE_FILE.write_text(json.dumps(players))


def answer(pin):
	players = json.loads(STATE_FILE.read_text())
	random.shuffle(players)
	for player in players:
		state = call("get_state", pin=pin, token=player["token"])
		if state.get("phase") != "question":
			print("no open question")
			return
		question_row = state["question"]["question_row"]
		# The guest API never reveals the answer, so the key lives here instead.
		right = ANSWER_KEY.get(state["question"]["question_text"])
		if right and random.random() < player["accuracy"]:
			option = right
		else:
			option = random.choice([o for o in "1234" if o != right])
		try:
			call(
				"submit_answer",
				pin=pin,
				token=player["token"],
				question_row=question_row,
				selected_option=option,
			)
			print(player["nickname"], "answered", option)
		except requests.HTTPError as error:
			print(player["nickname"], "rejected", error)
		time.sleep(random.uniform(0.3, 1.2))


if __name__ == "__main__":
	command, pin = sys.argv[1], sys.argv[2]
	{"join": join, "answer": answer}[command](pin)
