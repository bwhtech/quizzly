#!/usr/bin/env node
// Live-fire load generator: N guest players against a running session, over the
// same three transports a real phone uses — HTTP join, a socket.io room
// subscription, and one submit_answer per question.
//
//   QZ_PIN=010805 QZ_PLAYERS=5 node scripts/loadtest_live.mjs
//
// Unlike scripts/loadtest.py this needs no bench access and holds a real socket
// per player, so it measures the two things that HTTP-only driving cannot: how
// far apart a question lands across every device, and the end-of-game fan-out.
//
// env:
//   QZ_ORIGIN        target site            (default https://gajendra.fsn.frappe.cloud)
//   QZ_PIN           game pin  (required unless QZ_QUIZ + api key are set)
//   QZ_QUIZ          quiz name; with QZ_API_KEY/SECRET the run hosts itself:
//                    create session -> seat bots -> start -> play to the podium
//   QZ_PLAYERS       bot count              (default 5)
//   QZ_NAME_PREFIX   nickname prefix        (default bot)
//   QZ_JOIN_RATE     joins per minute, 0=unthrottled (default 0)
//   QZ_ANSWER_DELAY  ms to wait before submitting; 0 = worst-case herd (default 0)
//   QZ_TIMEOUT       overall budget seconds (default 900)
//   QZ_LEAVE         1 = leave_session on exit, only usable while still in the
//                    lobby and capped by its own 10/60s per-IP limit (default 0)
//   QZ_API_KEY       host api key    (only for self-hosted runs)
//   QZ_API_SECRET    host api secret (only for self-hosted runs)
//   QZ_OUT           write the raw report here as JSON (optional)

import { Agent, request } from "undici";
import { io } from "socket.io-client";

const ORIGIN = process.env.QZ_ORIGIN || "https://gajendra.fsn.frappe.cloud";
let PIN = process.env.QZ_PIN;
const QUIZ = process.env.QZ_QUIZ;
const API_KEY = process.env.QZ_API_KEY;
const API_SECRET = process.env.QZ_API_SECRET;
const HOSTED = Boolean(QUIZ && API_KEY && API_SECRET);
const PLAYERS = Number(process.env.QZ_PLAYERS || 5);
const NAME_PREFIX = process.env.QZ_NAME_PREFIX || "bot";
const JOIN_RATE = Number(process.env.QZ_JOIN_RATE || 0);
const ANSWER_DELAY = Number(process.env.QZ_ANSWER_DELAY || 0);
const TIMEOUT_MS = Number(process.env.QZ_TIMEOUT || 900) * 1000;
const LEAVE = process.env.QZ_LEAVE === "1";
const OUT = process.env.QZ_OUT;

if (!PIN && !HOSTED) {
	console.error("set QZ_PIN, or QZ_QUIZ + QZ_API_KEY + QZ_API_SECRET to host the run");
	process.exit(2);
}

const SITE = new URL(ORIGIN).hostname;
const API = `${ORIGIN}/api/method/quizzly.api`;
let ROOM_EVENT;

// One pool wide enough that a 1000-player salvo is never queued client-side; a
// queued request would be charged to the server as latency it did not spend.
const pool = new Agent({ connections: PLAYERS + 16, pipelining: 1 });

const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

async function callApi(method, params, httpMethod = "POST", asHost = false) {
	const started = Date.now();
	const isPost = httpMethod === "POST";
	const url = isPost
		? `${API}.${method}`
		: `${API}.${method}?${new URLSearchParams(params)}`;
	try {
		const response = await request(url, {
			method: httpMethod,
			dispatcher: pool,
			headers: {
				"content-type": "application/json",
				accept: "application/json",
				...(asHost
					? { authorization: `token ${API_KEY}:${API_SECRET}` }
					: { cookie: "sid=Guest" }),
			},
			body: isPost ? JSON.stringify(params) : undefined,
			headersTimeout: 60000,
			bodyTimeout: 60000,
		});
		const text = await response.body.text();
		const ms = Date.now() - started;
		if (response.statusCode !== 200) {
			return { ms, error: `http_${response.statusCode}`, detail: serverMessage(text) };
		}
		return { ms, data: JSON.parse(text).message };
	} catch (error) {
		return { ms: Date.now() - started, error: error.code || error.name };
	}
}

// frappe hides thrown messages inside a JSON-encoded _server_messages list
function serverMessage(text) {
	try {
		const messages = JSON.parse(JSON.parse(text)._server_messages || "[]");
		return messages.map((m) => JSON.parse(m).message).join("; ").slice(0, 120);
	} catch {
		return text.slice(0, 120);
	}
}

function percentile(sorted, p) {
	if (!sorted.length) return 0;
	const index = Math.min(sorted.length - 1, Math.ceil((p / 100) * sorted.length) - 1);
	return sorted[index];
}

function summarise(values) {
	const sorted = [...values].sort((a, b) => a - b);
	return {
		n: sorted.length,
		p50: Math.round(percentile(sorted, 50)),
		p95: Math.round(percentile(sorted, 95)),
		p99: Math.round(percentile(sorted, 99)),
		max: Math.round(sorted.at(-1) || 0),
	};
}

function tally(items) {
	const counts = {};
	for (const item of items) counts[item] = (counts[item] || 0) + 1;
	return counts;
}

async function joinAll() {
	const players = [];
	const failures = [];
	const latencies = [];
	const gap = JOIN_RATE > 0 ? 60000 / JOIN_RATE : 0;

	const attempts = Array.from({ length: PLAYERS }, (_, index) => async () => {
		if (gap) await sleep(index * gap);
		const nickname = `${NAME_PREFIX}${String(index).padStart(4, "0")}`;
		const result = await callApi("join_session", { pin: PIN, nickname });
		latencies.push(result.ms);
		if (result.error) {
			failures.push(`${result.error}${result.detail ? `: ${result.detail}` : ""}`);
			return;
		}
		players.push({ index, nickname, token: result.data.participant_token, events: [], submits: [] });
	});

	await Promise.all(attempts.map((run) => run()));
	return { players, failures, latencies };
}

function connect(player, onEvent) {
	return new Promise((resolve) => {
		// websocket-only: the real client starts on polling and upgrades, but a
		// generator that does the same doubles the handshake cost per player and
		// charges it to the server. Note this when reading connect timings.
		const socket = io(`${ORIGIN}/${SITE}`, {
			transports: ["websocket"],
			extraHeaders: { Origin: ORIGIN, Cookie: "sid=Guest" },
			reconnection: true,
		});
		const started = Date.now();
		player.socket = socket;

		socket.on("connect", () => {
			socket.emit("qz_join", PIN);
			if (player.connectMs === undefined) {
				player.connectMs = Date.now() - started;
				resolve(true);
			}
		});
		socket.on(ROOM_EVENT, (message) => onEvent(player, message));
		socket.on("connect_error", (error) => {
			if (player.connectMs === undefined) {
				player.connectError = error.message;
				player.connectMs = Date.now() - started;
				resolve(false);
			}
		});
		setTimeout(() => {
			if (player.connectMs === undefined) {
				player.connectError = "timeout";
				resolve(false);
			}
		}, 30000);
	});
}

async function main() {
	let session;
	if (HOSTED) {
		console.log(`==> creating session for quiz ${QUIZ}`);
		const created = await callApi("create_session", { quiz: QUIZ }, "POST", true);
		if (created.error) {
			console.error(`    could not create session: ${created.error} ${created.detail || ""}`);
			return 2;
		}
		session = created.data.session;
		PIN = created.data.game_pin;
		// without auto-advance the ticker waits on a host click that never comes
		await callApi("set_auto_advance", { session, enabled: 1 }, "POST", true);
		console.log(`    session=${session} pin=${PIN}`);
	}
	ROOM_EVENT = `qz_session_${PIN}`;

	console.log(`target=${ORIGIN} pin=${PIN} players=${PLAYERS} answer_delay=${ANSWER_DELAY}ms\n`);

	console.log("==> joining");
	const { players, failures, latencies } = await joinAll();
	console.log(`    seated ${players.length}/${PLAYERS}  join latency ${JSON.stringify(summarise(latencies))}`);
	if (failures.length) console.log(`    join failures: ${JSON.stringify(tally(failures))}`);
	if (!players.length) {
		console.error("nobody got in, aborting");
		return 2;
	}

	const questions = new Map(); // question_row -> {arrivals: [], submits: []}
	let podium = null;
	let finished;
	const done = new Promise((resolve) => {
		finished = resolve;
	});

	function onEvent(player, message) {
		const at = Date.now();
		player.events.push({ at, type: message.type });

		if (message.type === "question") {
			const row = message.question_row;
			if (!questions.has(row)) {
				questions.set(row, { index: message.q_index, arrivals: [], submits: [], errors: [] });
			}
			const bucket = questions.get(row);
			bucket.arrivals.push(at);
			if (!player.answered?.has(row)) {
				(player.answered ??= new Set()).add(row);
				submit(player, row, bucket);
			}
		}

		if (message.type === "podium" && !podium) {
			podium = { at, bytes: JSON.stringify(message).length, arrivals: [] };
		}
		if (message.type === "podium") podium.arrivals.push(at);
	}

	async function submit(player, row, bucket) {
		if (ANSWER_DELAY) await sleep(Math.random() * ANSWER_DELAY);
		const option = String(1 + (player.index % 4));
		const result = await callApi("submit_answer", {
			pin: PIN,
			token: player.token,
			question_row: row,
			selected_option: option,
		});
		if (result.error) bucket.errors.push(`${result.error}${result.detail ? `: ${result.detail}` : ""}`);
		else bucket.submits.push(result.ms);
	}

	console.log("==> opening sockets");
	const connectStarted = Date.now();
	const connected = await Promise.all(players.map((player) => connect(player, onEvent)));
	const live = connected.filter(Boolean).length;
	console.log(
		`    ${live}/${players.length} sockets live in ${Date.now() - connectStarted}ms  ` +
			`connect ${JSON.stringify(summarise(players.filter((p) => !p.connectError).map((p) => p.connectMs)))}`
	);
	const connectErrors = tally(players.filter((p) => p.connectError).map((p) => p.connectError));
	if (Object.keys(connectErrors).length) console.log(`    connect errors: ${JSON.stringify(connectErrors)}`);

	if (HOSTED) {
		console.log("\n==> starting the game");
		const started = await callApi("start_session", { session }, "POST", true);
		if (started.error) console.error(`    start failed: ${started.error} ${started.detail || ""}`);
	} else {
		console.log("\n==> waiting for the host to run the game (ctrl-c to stop)\n");
	}
	const watchdog = setInterval(() => {
		if (podium && podium.arrivals.length >= live) finished();
	}, 500);
	const timeout = setTimeout(finished, TIMEOUT_MS);
	await done;
	clearInterval(watchdog);
	clearTimeout(timeout);

	const report = { origin: ORIGIN, pin: PIN, session, players: players.length, sockets: live, questions: [] };

	console.log("=== per question ===");
	for (const [row, bucket] of questions) {
		const first = Math.min(...bucket.arrivals);
		const skew = bucket.arrivals.map((at) => at - first);
		const line = {
			q: bucket.index,
			delivered: `${bucket.arrivals.length}/${live}`,
			skew_ms: summarise(skew),
			submit_ms: summarise(bucket.submits),
			ok: bucket.submits.length,
			errors: tally(bucket.errors),
		};
		report.questions.push({ row, ...line });
		console.log(
			`  Q${line.q}  delivered ${line.delivered}  ` +
				`skew p50=${line.skew_ms.p50} p95=${line.skew_ms.p95} max=${line.skew_ms.max}ms  ` +
				`submit p50=${line.submit_ms.p50} p95=${line.submit_ms.p95} max=${line.submit_ms.max}ms  ` +
				`ok=${line.ok}  errors=${JSON.stringify(line.errors)}`
		);
	}

	if (podium) {
		const first = Math.min(...podium.arrivals);
		const skew = summarise(podium.arrivals.map((at) => at - first));
		report.podium = { bytes: podium.bytes, delivered: podium.arrivals.length, skew_ms: skew };
		console.log(
			`\n=== podium ===\n  payload ${(podium.bytes / 1024).toFixed(1)}KB x ${podium.arrivals.length} sockets ` +
				`= ${((podium.bytes * podium.arrivals.length) / 1048576).toFixed(1)}MB fan-out  ` +
				`skew p50=${skew.p50} p95=${skew.p95} max=${skew.max}ms`
		);
	} else {
		console.log("\n=== podium ===\n  never arrived");
	}

	if (OUT) {
		await (await import("node:fs/promises")).writeFile(OUT, JSON.stringify(report, null, 2));
		console.log(`\nreport written to ${OUT}`);
	}

	for (const player of players) player.socket?.close();

	// leave_session is capped 10/60s per IP, so this only clears a smoke run. A
	// full-size run leaves its rows behind for the bench-side cleanup snippet.
	if (LEAVE) {
		for (const player of players) {
			await callApi("leave_session", { pin: PIN, token: player.token });
		}
		console.log(`\nleft ${players.length} players`);
	}
	return 0;
}

process.exitCode = await main();
process.exit(process.exitCode);
