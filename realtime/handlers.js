const GAME_PIN = /^\d{6}$/;

function trivia_tap_handlers(socket) {
	socket.on("qz_join", (pin) => {
		if (typeof pin === "string" && GAME_PIN.test(pin)) {
			socket.join("qz_session_" + pin);
		}
	});

	socket.on("qz_leave", (pin) => {
		if (typeof pin === "string" && GAME_PIN.test(pin)) {
			socket.leave("qz_session_" + pin);
		}
	});
}

module.exports = trivia_tap_handlers;
