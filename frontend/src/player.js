const KEY = "tt_player";

export function savePlayer(joinResult) {
	localStorage.setItem(
		KEY,
		JSON.stringify({
			token: joinResult.participant_token,
			participant: joinResult.participant,
			nickname: joinResult.nickname,
			avatar: joinResult.avatar,
			pin: joinResult.game_pin,
			participants: joinResult.participants,
		})
	);
}

export function loadPlayer() {
	try {
		return JSON.parse(localStorage.getItem(KEY));
	} catch {
		return null;
	}
}

export function clearPlayer() {
	localStorage.removeItem(KEY);
}
