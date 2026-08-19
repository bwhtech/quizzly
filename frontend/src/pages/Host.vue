<template>
	<div class="flex h-full flex-col overflow-y-auto bg-night">
		<!-- A live game owns the projector; nav on it is something the room looks at instead of the PIN. -->
		<template v-if="!session">
			<HostBar />
			<div
				class="mx-auto flex w-full max-w-2xl flex-1 flex-col justify-center gap-8 p-5 sm:p-8"
			>
				<div>
					<p class="font-mono text-[11px] uppercase tracking-[0.28em] text-accent">
						Host
					</p>
					<h1 class="mt-2 font-display text-4xl font-extrabold text-paper sm:text-5xl">
						Pick a quiz
					</h1>
				</div>
				<p v-if="error" class="text-alert">{{ error }}</p>
				<div v-if="quizzes.length" class="flex flex-col gap-2">
					<button
						v-for="(quiz, index) in quizzes"
						:key="quiz.name"
						class="group flex items-center gap-4 rounded-2xl border border-haze bg-dusk px-5 py-4 text-left transition hover:border-ember"
						@click="createSession(quiz.name)"
					>
						<span class="font-mono text-xs tabular-nums text-paper/35">
							{{ String(index + 1).padStart(2, "0") }}
						</span>
						<span class="flex-1 font-display text-xl font-bold text-paper">
							{{ quiz.title }}
						</span>
						<span class="text-paper/25 transition group-hover:text-alert">→</span>
					</button>
				</div>
				<p v-else-if="loaded" class="text-paper/50">
					No quizzes yet. Write your first one.
				</p>
				<RouterLink v-if="!quizzes.length" class="ctl self-start" to="/host/quizzes/new">
					New quiz
				</RouterLink>
			</div>
		</template>

		<!-- Lobby -->
		<template v-else-if="phase === 'lobby'">
			<div class="flex flex-1 flex-col justify-center gap-8 p-5 sm:gap-12 sm:p-8">
				<div class="flex flex-wrap items-center justify-center gap-8 sm:gap-14">
					<div class="min-w-0 text-center sm:text-left">
						<!-- inline, not a flex row: the icon has to follow the last line when a
						     long join host wraps on a phone -->
						<p
							class="break-all font-mono text-xs tracking-wide text-accent sm:text-sm"
						>
							Join at {{ joinHost }}
							<button
								class="ml-1 inline-block translate-y-1 rounded-md p-1 text-paper/30 transition hover:bg-dusk hover:text-paper"
								:title="copied ? 'Copied' : `Copy ${joinUrl}`"
								:aria-label="`Copy ${joinUrl}`"
								@click="copyJoinUrl"
							>
								<svg
									class="size-4"
									viewBox="0 0 24 24"
									fill="none"
									stroke="currentColor"
									stroke-width="2"
									stroke-linecap="round"
									stroke-linejoin="round"
								>
									<polyline v-if="copied" points="20 6 9 17 4 12" />
									<template v-else>
										<rect x="9" y="9" width="13" height="13" rx="2" ry="2" />
										<path
											d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"
										/>
									</template>
								</svg>
							</button>
						</p>
						<p
							class="mt-3 font-mono text-6xl font-bold tracking-[0.08em] text-paper sm:text-8xl"
						>
							{{ session.game_pin }}
						</p>
						<p class="mt-3 text-sm text-paper/45 sm:text-base">
							or point a phone camera at the code
						</p>
					</div>
					<button v-if="qrDataUrl" class="group" @click="qrFullscreen = true">
						<img
							:src="qrDataUrl"
							alt="Join QR code"
							class="size-40 rounded-2xl bg-card p-2 transition group-hover:scale-105 sm:size-48"
						/>
						<span
							class="mt-2 block font-mono text-[11px] uppercase tracking-wider text-paper/35 transition group-hover:text-paper/70"
						>
							Click to enlarge
						</span>
					</button>
				</div>

				<div class="flex flex-col items-center gap-5">
					<p
						v-if="participants.length"
						class="font-mono text-xs uppercase tracking-[0.28em] text-paper/40"
					>
						{{ participants.length }}
						{{ participants.length === 1 ? "player" : "players" }} in
					</p>
					<div class="flex max-w-5xl flex-wrap justify-center gap-2.5">
						<!-- The chip itself is not the kick target: a full-name-sized button is
						     too easy to hit by accident on a projector. -->
						<div
							v-for="participant in participants"
							:key="participant.name"
							class="group relative flex items-center gap-2 rounded-full border border-haze bg-dusk py-1 pl-1 pr-4 text-base font-medium text-paper sm:gap-3 sm:pr-5 sm:text-xl"
						>
							<AvatarPic
								:id="participant.avatar"
								:nickname="participant.nickname"
								:size="40"
							/>
							<span>{{ participant.nickname }}</span>
							<button
								class="absolute -right-1 -top-1 grid size-6 place-items-center rounded-full bg-haze text-sm leading-none text-paper opacity-0 transition hover:bg-ember hover:text-sunk focus-visible:opacity-100 group-hover:opacity-100"
								:aria-label="`Remove ${participant.nickname}`"
								@click="kick(participant)"
							>
								×
							</button>
						</div>
					</div>
					<p v-if="!participants.length" class="text-paper/35">
						Waiting for the first player…
					</p>
				</div>

				<div class="flex flex-wrap items-center justify-center gap-3">
					<button class="ctl" :data-on="lobbyLocked" @click="toggleLock">
						{{ lobbyLocked ? "Lobby locked" : "Lock lobby" }}
					</button>
					<button class="ctl" :data-on="autoAdvance" @click="toggleAutoAdvance">
						Auto-advance {{ autoAdvance ? "on" : "off" }}
					</button>
					<button class="ctl" @click="toggleMute">
						{{ muted ? "Sound off" : "Sound on" }}
					</button>
					<ThemeButton class="ctl" />
					<button class="ctl" @click="end">Exit</button>
					<button
						class="ctl ctl-go"
						:disabled="starting || !participants.length"
						@click="start"
					>
						{{ starting ? "Starting…" : "Start game" }}
					</button>
				</div>
				<p v-if="error" class="text-center text-alert">{{ error }}</p>
			</div>

			<dialog
				ref="qrDialog"
				class="qz-dialog max-h-none overflow-hidden border-0 bg-transparent p-0"
				@cancel.prevent="qrFullscreen = false"
				@click="qrFullscreen = false"
			>
				<img
					:src="qrDataUrl"
					alt="Join QR code"
					class="size-[min(78vh,88vw)] rounded-3xl bg-card p-4"
				/>
				<p class="mt-4 text-center font-mono text-2xl tracking-[0.08em] text-paper">
					{{ session.game_pin }}
				</p>
			</dialog>
		</template>

		<!-- Podium -->
		<template v-else-if="phase === 'podium'">
			<div
				class="flex flex-1 flex-col items-center justify-center gap-8 p-5 sm:gap-10 sm:p-8"
			>
				<h1 class="font-display text-4xl font-extrabold text-paper sm:text-6xl">
					Final results
				</h1>
				<div class="flex items-end justify-center gap-2 sm:gap-4">
					<div
						v-for="entry in podiumOrder"
						:key="entry.nickname"
						class="flex w-24 flex-col items-center gap-2 sm:w-36"
					>
						<AvatarPic
							:id="entry.avatar"
							:nickname="entry.nickname"
							:size="entry.rank === 1 ? 88 : 64"
						/>
						<span
							class="max-w-full truncate font-display text-base font-bold text-paper sm:text-xl"
						>
							{{ entry.nickname }}
						</span>
						<span class="font-mono text-sm tabular-nums text-paper/50">
							{{ entry.score }}
						</span>
						<div
							class="podium-rise flex w-full items-start justify-center rounded-t-2xl pt-3 font-mono text-2xl font-bold text-sunk sm:text-3xl"
							:class="PODIUM_FILL[entry.rank]"
							:style="{ height: `${180 - (entry.rank - 1) * 45}px` }"
						>
							{{ entry.rank }}
						</div>
					</div>
				</div>
				<ol class="w-full max-w-md">
					<li
						v-for="entry in leaderboard"
						:key="entry.nickname"
						class="flex items-center justify-between gap-3 border-b border-haze py-2.5 text-base text-paper/70 sm:text-lg"
					>
						<span class="flex min-w-0 items-center gap-3">
							<span
								class="w-5 shrink-0 font-mono text-xs tabular-nums text-paper/35"
							>
								{{ entry.rank }}
							</span>
							<AvatarPic :id="entry.avatar" :nickname="entry.nickname" :size="28" />
							<span class="truncate">{{ entry.nickname }}</span>
						</span>
						<span class="shrink-0 font-mono tabular-nums">{{ entry.score }}</span>
					</li>
				</ol>
				<button class="ctl" @click="reset">New game</button>
			</div>
		</template>

		<!-- Read time: question only, no answers yet -->
		<template v-else-if="phase === 'get_ready'">
			<div
				class="flex flex-1 flex-col items-center justify-center gap-8 p-5 text-center sm:gap-10 sm:p-8"
			>
				<p class="font-mono text-xs uppercase tracking-[0.28em] text-paper/40">
					Question {{ (question?.q_index ?? 0) + 1 }} of {{ question?.total }}
				</p>
				<h1
					class="max-w-4xl font-display text-3xl font-extrabold leading-tight text-paper sm:text-6xl"
				>
					{{ question?.question_text }}
				</h1>
				<DrainRing
					:percent="timerPercent"
					:seconds="Math.ceil(remaining)"
					:size="140"
					color="rgb(var(--accent))"
				/>
			</div>
		</template>

		<!-- Question / results -->
		<template v-else>
			<!-- m-auto, not justify-center: a centered flex column clips its top when it overflows -->
			<div class="flex flex-1 flex-col p-4 sm:p-8">
				<div class="m-auto flex w-full max-w-6xl flex-col gap-5 sm:gap-7">
					<!-- on a phone the question takes its own row: a timer and a counter beside it
					     leave the text in a column too narrow to read -->
					<div class="flex flex-wrap items-center gap-4 sm:gap-6">
						<DrainRing
							v-if="phase === 'question'"
							:percent="timerPercent"
							:seconds="Math.ceil(remaining)"
							:size="96"
							:color="remaining <= 5 ? 'rgb(var(--alert))' : 'rgb(var(--ok))'"
						/>
						<div class="order-last w-full min-w-0 sm:order-none sm:w-auto sm:flex-1">
							<p class="font-mono text-xs uppercase tracking-[0.28em] text-paper/40">
								Question {{ (question?.q_index ?? 0) + 1 }} of
								{{ question?.total }}
							</p>
							<h1
								class="mt-2 font-display text-2xl font-extrabold leading-tight text-paper sm:text-4xl"
							>
								{{ question?.question_text }}
							</h1>
						</div>
						<p
							v-if="phase === 'question'"
							class="ml-auto shrink-0 font-mono text-sm tabular-nums text-paper/40 sm:ml-0"
						>
							{{ answerCount }} answered
						</p>
					</div>

					<img
						v-if="question?.image_url"
						:src="question.image_url"
						alt=""
						class="max-h-[22vh] w-full object-contain sm:max-h-[40vh]"
					/>

					<div class="grid grid-cols-1 gap-3 sm:grid-cols-2">
						<div
							v-for="shape in visibleShapes"
							:key="shape.id"
							class="flex items-center gap-3 rounded-2xl px-4 py-4 transition sm:gap-5 sm:px-6 sm:py-7"
							:class="[shape.fill, dimmed(shape.id) ? 'opacity-25' : '']"
						>
							<svg
								class="size-7 shrink-0 fill-sunk/55 sm:size-9"
								viewBox="0 0 24 24"
							>
								<path :d="shape.path" />
							</svg>
							<span
								class="flex-1 font-display text-lg font-extrabold text-sunk sm:text-2xl"
							>
								{{ question.options[Number(shape.id) - 1] }}
							</span>
							<span
								v-if="phase === 'closed' && shape.id === String(correctOption)"
								class="text-3xl text-sunk"
								>✓</span
							>
						</div>
					</div>

					<div
						v-if="phase === 'closed' && explainer"
						class="flex flex-col gap-4 rounded-2xl border border-haze bg-dusk p-4 sm:flex-row sm:items-center sm:gap-6 sm:p-6"
					>
						<img
							v-if="explainer.image"
							:src="explainer.image"
							alt=""
							class="max-h-[22vh] w-full object-contain sm:max-h-[30vh] sm:w-2/5"
						/>
						<p
							v-if="explainer.text"
							class="flex-1 whitespace-pre-line text-lg leading-snug text-paper/80 sm:text-2xl"
						>
							{{ explainer.text }}
						</p>
					</div>

					<template v-if="phase === 'closed'">
						<div class="flex h-32 w-full items-stretch gap-3">
							<div
								v-for="shape in visibleShapes"
								:key="shape.id"
								class="flex flex-1 flex-col gap-1.5"
							>
								<span
									class="text-center font-mono text-sm tabular-nums text-paper/60"
								>
									{{ distribution[shape.id] || 0 }}
								</span>
								<div class="flex flex-1 flex-col justify-end rounded-t-lg bg-dusk">
									<div
										class="rounded-t-lg transition-[height] duration-500"
										:class="shape.fill"
										:style="{ height: `${barHeight(shape.id)}%` }"
									/>
								</div>
							</div>
						</div>

						<div class="flex flex-wrap items-start justify-between gap-6 sm:gap-8">
							<ol class="w-full flex-1 sm:min-w-64">
								<li
									v-for="(entry, index) in top5"
									:key="entry.nickname"
									class="flex items-center justify-between gap-3 border-b border-haze py-2 text-base text-paper/70 sm:text-lg"
								>
									<span class="flex min-w-0 items-center gap-3">
										<span
											class="w-5 shrink-0 font-mono text-xs tabular-nums text-paper/35"
										>
											{{ index + 1 }}
										</span>
										<AvatarPic
											:id="entry.avatar"
											:nickname="entry.nickname"
											:size="28"
										/>
										<span class="truncate">{{ entry.nickname }}</span>
									</span>
									<span class="shrink-0 font-mono tabular-nums">{{
										entry.score
									}}</span>
								</li>
							</ol>
							<ul class="w-full flex-1 space-y-2 text-base text-paper/70 sm:text-lg">
								<li
									v-for="entry in streaks"
									:key="entry.nickname"
									class="flex items-center gap-2"
								>
									<AvatarPic
										:id="entry.avatar"
										:nickname="entry.nickname"
										:size="28"
									/>
									🔥 {{ entry.nickname }} is on a {{ entry.streak }} answer
									streak
								</li>
							</ul>
						</div>
					</template>

					<div class="flex flex-wrap items-center gap-3">
						<button v-if="phase === 'question'" class="ctl" @click="skip">Skip</button>
						<button v-if="phase === 'closed'" class="ctl ctl-go" @click="next">
							Next question
						</button>
						<button
							class="ctl"
							:data-on="autoAdvance"
							@click="toggleOption('auto_advance', autoAdvance)"
						>
							Auto-advance {{ autoAdvance ? "on" : "off" }}
						</button>
						<button
							class="ctl"
							:data-on="showExplainer"
							@click="toggleOption('show_explainer', showExplainer)"
						>
							Explainer {{ showExplainer ? "on" : "off" }}
						</button>
						<button class="ctl" @click="end">End game</button>
						<p v-if="error" class="text-alert">{{ error }}</p>
					</div>
				</div>
			</div>
		</template>
	</div>
</template>

<script setup>
import { computed, inject, onMounted, ref, watch } from "vue";
import QRCode from "qrcode";
import { call, readError } from "@/api";
import { confirm } from "@/confirm";
import { SHAPES, readExplainer, useCountdown, useSessionRoom } from "@/game";
import AvatarPic from "@/components/AvatarPic.vue";
import ThemeButton from "@/components/ThemeButton.vue";
import DrainRing from "@/components/DrainRing.vue";
import HostBar from "@/components/HostBar.vue";
import { initSound, muted, playCue, toggleMute } from "@/sound";

const PODIUM_FILL = { 1: "bg-gold", 2: "bg-lagoon", 3: "bg-orchid" };
// remembered so a reload on the podium restores it: get_host_state only auto-finds live sessions
const HOSTED_SESSION_KEY = "qz_hosted_session";

const socket = inject("$socket");
const {
	remaining,
	total: windowSeconds,
	start: startCountdown,
	stop: stopCountdown,
} = useCountdown();

const quizzes = ref([]);
const loaded = ref(false);
const session = ref(null);
const phase = ref("lobby");
const participants = ref([]);
const lobbyLocked = ref(false);
const autoAdvance = ref(false);
const showExplainer = ref(true);
const explainer = ref(null);
const question = ref(null);
const answerCount = ref(0);
const distribution = ref({});
const correctOption = ref(null);
const top5 = ref([]);
const streaks = ref([]);
const leaderboard = ref([]);
const qrDataUrl = ref("");
const qrFullscreen = ref(false);
const qrDialog = ref(null);
const copied = ref(false);
const starting = ref(false);
const error = ref("");

watch(qrFullscreen, (open) => (open ? qrDialog.value.showModal() : qrDialog.value.close()));

const joinUrl = computed(
	() => `${window.location.origin}/quizzly/join?pin=${session.value.game_pin}`
);

// The projector shows where to go, not the whole query string.
const joinHost = computed(() => `${window.location.host}/quizzly/join`);

const timerPercent = computed(() =>
	windowSeconds.value ? (remaining.value / windowSeconds.value) * 100 : 0
);

const visibleShapes = computed(() =>
	SHAPES.filter((shape) => question.value?.options[Number(shape.id) - 1])
);

watch(
	() => Math.ceil(remaining.value),
	(secondsLeft) => {
		if (phase.value === "question" && secondsLeft > 0 && secondsLeft <= 5) playCue("tick");
	}
);

// tallest bar fills the chart; the rest scale against it
const barHeight = (optionId) => {
	const counts = Object.values(distribution.value);
	const max = Math.max(1, ...counts);
	// keep a sliver visible so an empty bar still reads as a bar
	return Math.max(3, ((distribution.value[optionId] || 0) / max) * 100);
};

const dimmed = (optionId) => phase.value === "closed" && optionId !== String(correctOption.value);

// 2nd, 1st, 3rd — the winner stands in the middle
const podiumOrder = computed(() =>
	[leaderboard.value[1], leaderboard.value[0], leaderboard.value[2]].filter(Boolean)
);

function onSessionEvent(message) {
	if (message.type === "lobby_update") {
		participants.value = message.participants;
		lobbyLocked.value = Boolean(message.lobby_locked);
	} else if (message.type === "get_ready") {
		phase.value = "get_ready";
		question.value = { ...message, options: [] };
		startCountdown(message.seconds);
	} else if (message.type === "question") {
		question.value = message;
		answerCount.value = 0;
		correctOption.value = null;
		phase.value = "question";
		startCountdown(message.window_ms / 1000);
	} else if (message.type === "answer_count") {
		answerCount.value = message.count;
	} else if (message.type === "question_closed") {
		stopCountdown();
		distribution.value = message.distribution;
		correctOption.value = message.correct_option;
		top5.value = message.top_5;
		streaks.value = message.streaks;
		explainer.value = readExplainer(message);
		phase.value = "closed";
	} else if (message.type === "podium") {
		stopCountdown();
		leaderboard.value = message.leaderboard;
		phase.value = "podium";
		playCue("podium");
	}
}

// Level H redundancy is what buys the room to punch the logo over the middle.
async function renderQr(url) {
	const canvas = document.createElement("canvas");
	await QRCode.toCanvas(canvas, url, {
		margin: 1,
		width: 800,
		errorCorrectionLevel: "H",
		color: { dark: "#16111F", light: "#F4F0FA" },
	});
	const logo = new Image();
	logo.src = "/assets/quizzly/images/quizzly-logo.svg";
	try {
		await logo.decode();
	} catch {
		return canvas.toDataURL(); // a missing logo is not worth losing the code over
	}
	const badge = Math.round(canvas.width * 0.2);
	const at = Math.round((canvas.width - badge) / 2);
	const pad = Math.round(badge * 0.12);
	const context = canvas.getContext("2d");
	context.fillStyle = "#F4F0FA";
	context.fillRect(at - pad, at - pad, badge + pad * 2, badge + pad * 2);
	context.drawImage(logo, at, at, badge, badge);
	return canvas.toDataURL();
}

async function copyJoinUrl() {
	try {
		await navigator.clipboard.writeText(joinUrl.value);
		copied.value = true;
		setTimeout(() => (copied.value = false), 1500);
	} catch {
		error.value = `Copy failed. The link is ${joinUrl.value}`;
	}
}

async function applyState(state) {
	session.value = { name: state.session, game_pin: state.game_pin };
	localStorage.setItem(HOSTED_SESSION_KEY, state.session);
	participants.value = state.participants || [];
	lobbyLocked.value = Boolean(state.lobby_locked);
	autoAdvance.value = Boolean(state.auto_advance);
	showExplainer.value = Boolean(state.show_explainer);
	top5.value = state.top_5 || [];
	qrDataUrl.value = await renderQr(joinUrl.value);

	if (state.status === "Lobby") {
		starting.value = false;
		phase.value = "lobby";
	} else if (state.leaderboard) {
		leaderboard.value = state.leaderboard;
		phase.value = "podium";
	} else if (state.phase === "question") {
		question.value = state.question;
		correctOption.value = null;
		answerCount.value = state.answer_count;
		phase.value = "question";
		startCountdown(state.remaining_seconds);
	} else if (state.phase === "closed") {
		question.value = state.question;
		distribution.value = state.distribution || {};
		correctOption.value = state.question.correct_option;
		explainer.value = readExplainer(state);
		phase.value = "closed";
	} else {
		phase.value = "get_ready";
		// options stay hidden during read time, same as the live get_ready event
		question.value = { ...state.question, options: [] };
		startCountdown(state.remaining_seconds);
	}
}

async function refresh() {
	await applyState(await loadHostState());
}

async function loadHostState() {
	const remembered = localStorage.getItem(HOSTED_SESSION_KEY);
	if (remembered) {
		try {
			return await call("quizzly.api.get_host_state", { session: remembered });
		} catch {
			localStorage.removeItem(HOSTED_SESSION_KEY);
		}
	}
	return await call("quizzly.api.get_host_state");
}

onMounted(async () => {
	initSound("host");
	try {
		const state = await loadHostState();
		if (state.session) {
			await applyState(state);
			useSessionRoom(socket, state.game_pin, onSessionEvent, refresh);
			return;
		}
		quizzes.value = await call("quizzly.api.list_quizzes");
		loaded.value = true;
	} catch (e) {
		error.value = readError(e);
	}
});

async function createSession(quiz) {
	error.value = "";
	try {
		const created = await call("quizzly.api.create_session", { quiz });
		await applyState(await call("quizzly.api.get_host_state", { session: created.session }));
		useSessionRoom(socket, session.value.game_pin, onSessionEvent, refresh);
	} catch (e) {
		error.value = readError(e);
	}
}

async function hostCall(method, params = {}) {
	error.value = "";
	try {
		return await call(method, { session: session.value.name, ...params });
	} catch (e) {
		error.value = readError(e);
		// the screen is out of step with the server (a missed event, a stale tab): repair it
		await refresh().catch(() => {});
	}
}

async function toggleLock() {
	const lobby = await hostCall(
		lobbyLocked.value ? "quizzly.api.unlock_lobby" : "quizzly.api.lock_lobby"
	);
	if (lobby) lobbyLocked.value = Boolean(lobby.lobby_locked);
}

async function toggleOption(option, current) {
	const result = await hostCall("quizzly.api.set_session_option", {
		option,
		enabled: current.value ? 0 : 1,
	});
	if (result) current.value = Boolean(result[option]);
}

async function kick(participant) {
	const ok = await confirm(`Remove ${participant.nickname} from the game?`, {
		action: "Remove",
		danger: true,
	});
	if (!ok) return;
	await hostCall("quizzly.api.kick_participant", { participant: participant.name });
}

// the lobby only clears when the worker's first event lands, so the button has to
// stay down until then: a second start_session throws "Session has already started"
async function start() {
	starting.value = true;
	if (!(await hostCall("quizzly.api.start_session"))) starting.value = false;
}
const next = () => hostCall("quizzly.api.next_question");
const skip = () => hostCall("quizzly.api.skip_question");

async function end() {
	const players = participants.value.length;
	const inLobby = phase.value === "lobby";
	const prompt = inLobby
		? "Close this lobby and pick another quiz?"
		: `End the game for all ${players} ${players === 1 ? "player" : "players"}?`;
	if (!(await confirm(prompt, { action: inLobby ? "Close lobby" : "End game", danger: true })))
		return;
	// a cancelled lobby has no podium to land on, so the host goes back to the quiz list
	if ((await hostCall("quizzly.api.end_session")) && inLobby) reset();
}

function reset() {
	localStorage.removeItem(HOSTED_SESSION_KEY);
	window.location.reload();
}
</script>
