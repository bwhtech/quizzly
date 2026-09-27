const GAME_PIN = /^\d{6}$/;

function trivia_tap_handlers(socket) {
	socket.on("tt_join", (pin) => {
		if (typeof pin === "string" && GAME_PIN.test(pin)) {
			socket.join("tt_session_" + pin);
		}
	});

	socket.on("tt_leave", (pin) => {
		if (typeof pin === "string" && GAME_PIN.test(pin)) {
			socket.leave("tt_session_" + pin);
		}
	});
}

module.exports = trivia_tap_handlers;
