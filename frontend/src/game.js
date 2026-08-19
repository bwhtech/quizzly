import { onBeforeUnmount, ref } from "vue";

const SILENCE_LIMIT_MS = 20000;
const OFFLINE_RESYNC_MS = 3000;

// Colors are spelled out as full class names: Tailwind only generates what it can see.
export const SHAPES = [
	{
		id: "1",
		name: "bolt",
		fill: "bg-ember",
		svgFill: "fill-ember",
		hover: "hover:brightness-110",
		ink: "text-sunk",
		path: "M13.5 1.5 L4 13.5 H10 L8.5 22.5 L20 9.5 H13 Z",
	},
	{
		id: "2",
		name: "spark",
		fill: "bg-lagoon",
		svgFill: "fill-lagoon",
		hover: "hover:brightness-110",
		ink: "text-sunk",
		path: "M12 1 C13 8.5 15.5 11 23 12 C15.5 13 13 15.5 12 23 C11 15.5 8.5 13 1 12 C8.5 11 11 8.5 12 1 Z",
	},
	{
		id: "3",
		name: "moon",
		fill: "bg-gold",
		svgFill: "fill-gold",
		hover: "hover:brightness-110",
		ink: "text-sunk",
		path: "M17 2 a10 10 0 1 0 0 20 12 12 0 0 1 0-20 z",
	},
	{
		id: "4",
		name: "hex",
		fill: "bg-orchid",
		svgFill: "fill-orchid",
		hover: "hover:brightness-110",
		ink: "text-sunk",
		path: "M12 1.5 L21 6.75 V17.25 L12 22.5 L3 17.25 V6.75 Z",
	},
];

// The server omits both keys when there is nothing to show, so absent means no card.
export function readExplainer(payload) {
	if (!payload?.explanation && !payload?.explanation_image) return null;
	return { text: payload.explanation, image: payload.explanation_image };
}

export function shapeFor(optionId) {
	return SHAPES[Number(optionId) - 1];
}

// Deterministic per player and question, so a reload keeps the same order.
export function optionOrder(question, seed) {
	const ids = ["1", "2", "3", "4"].filter((id) => question.options[Number(id) - 1]);
	if (!question.randomize_answer_order) return ids;
	const random = mulberry32(hash(`${seed}:${question.question_row}`));
	for (let i = ids.length - 1; i > 0; i--) {
		const j = Math.floor(random() * (i + 1));
		[ids[i], ids[j]] = [ids[j], ids[i]];
	}
	return ids;
}

function hash(text) {
	let value = 2166136261;
	for (let i = 0; i < text.length; i++) {
		value = Math.imul(value ^ text.charCodeAt(i), 16777619);
	}
	return value >>> 0;
}

function mulberry32(seed) {
	return function () {
		seed = (seed + 0x6d2b79f5) | 0;
		let t = Math.imul(seed ^ (seed >>> 15), 1 | seed);
		t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
		return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
	};
}

/**
 * Subscribe to a session's realtime room.
 *
 * socket.io reconnects on its own but the server-side room membership is gone,
 * so every reconnect has to re-emit qz_join. `resync` then repairs whatever was
 * missed while the socket was down.
 */
export function useSessionRoom(socket, pin, onEvent, resync) {
	const eventName = `qz_session_${pin}`;
	let lastEventAt = Date.now();

	function handle(message) {
		lastEventAt = Date.now();
		onEvent(message);
	}

	function join() {
		socket.emit("qz_join", pin);
		lastEventAt = Date.now();
		resync();
	}

	socket.on(eventName, handle);
	socket.on("connect", join);
	join();

	// A socket can go quiet without ever firing `connect` again: the room membership
	// is lost or a reconnect never lands, and the screen then freezes for good. Long
	// silences are normal between questions, so a live socket is only rejoined after a
	// very quiet stretch. Once the socket is down this resync is the whole transport,
	// and a quiz is unplayable if a question takes 20 seconds to show up.
	const watchdog = setInterval(() => {
		const limit = socket.connected ? SILENCE_LIMIT_MS : OFFLINE_RESYNC_MS;
		if (Date.now() - lastEventAt > limit) join();
	}, 1000);

	let stopped = false;
	function stop() {
		if (stopped) return;
		stopped = true;
		clearInterval(watchdog);
		socket.off(eventName, handle);
		socket.off("connect", join);
		socket.emit("qz_leave", pin);
	}

	onBeforeUnmount(stop);
	return stop;
}

/** Local countdown. Ticks off elapsed wall time, never off the server clock. */
export function useCountdown() {
	const remaining = ref(0);
	const total = ref(0);
	let timer = null;

	function start(seconds) {
		stop();
		total.value = seconds;
		remaining.value = seconds;
		const endsAt = Date.now() + seconds * 1000;
		timer = setInterval(() => {
			remaining.value = Math.max(0, (endsAt - Date.now()) / 1000);
			if (remaining.value === 0) stop();
		}, 100);
	}

	function stop() {
		if (timer) clearInterval(timer);
		timer = null;
	}

	onBeforeUnmount(stop);
	return { remaining, total, start, stop };
}
