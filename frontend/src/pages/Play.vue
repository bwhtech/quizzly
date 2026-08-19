<template>
	<div class="flex h-full flex-col bg-night">
		<header
			v-if="player && phase !== 'kicked'"
			class="flex shrink-0 items-center justify-between gap-3 border-b border-haze px-4 py-2.5"
		>
			<span class="flex min-w-0 items-center gap-2.5">
				<AvatarPic :id="player.avatar" :nickname="player.nickname" :size="30" />
				<span class="truncate font-display text-base font-bold text-paper">
					{{ player.nickname }}
				</span>
			</span>
			<span class="flex items-center gap-3">
				<button
					type="button"
					class="text-lg leading-none opacity-60 transition hover:opacity-100"
					:aria-label="muted ? 'Turn sound on' : 'Turn sound off'"
					@click="toggleMute"
				>
					{{ muted ? "🔇" : "🔊" }}
				</button>
				<ThemeButton
					class="text-lg leading-none opacity-60 transition hover:opacity-100"
				/>
				<span class="font-mono text-sm font-bold tabular-nums text-accent">{{
					score
				}}</span>
				<button
					v-if="phase !== 'podium'"
					type="button"
					class="rounded-full border border-haze px-3 py-1 text-xs text-paper/50 transition hover:border-ember hover:text-alert"
					@click="leave"
				>
					Leave
				</button>
			</span>
		</header>

		<template v-if="phase === 'question'">
			<div class="flex shrink-0 items-center gap-4 px-4 py-4">
				<DrainRing
					:percent="timerPercent"
					:seconds="Math.ceil(remaining)"
					:size="56"
					:color="urgentColor"
				/>
				<div class="min-w-0">
					<p class="font-mono text-[10px] uppercase tracking-[0.22em] text-paper/40">
						Question {{ qIndex + 1 }} of {{ total }}
					</p>
					<h1 class="mt-1 font-display text-lg font-bold leading-snug text-paper">
						{{ question.question_text }}
					</h1>
				</div>
			</div>
			<img
				v-if="question.image_url"
				:src="question.image_url"
				alt=""
				class="max-h-[26vh] w-full shrink-0 object-contain px-4 pb-2"
			/>
			<div class="grid flex-1 grid-cols-2 grid-rows-2 gap-2 p-2">
				<button
					v-for="optionId in orderedOptions"
					:key="optionId"
					class="flex flex-col items-start justify-between rounded-2xl p-4 text-left transition active:scale-[0.97]"
					:class="[shapeFor(optionId).fill, shapeFor(optionId).hover]"
					@click="answer(optionId)"
				>
					<svg class="h-9 w-9 fill-sunk/55" viewBox="0 0 24 24">
						<path :d="shapeFor(optionId).path" />
					</svg>
					<span class="font-display text-xl font-extrabold leading-tight text-sunk">
						{{ question.options[Number(optionId) - 1] }}
					</span>
				</button>
			</div>
			<p v-if="error" class="px-4 pb-3 text-center text-sm text-alert">{{ error }}</p>
		</template>

		<main
			v-else
			class="flex flex-1 flex-col items-center justify-center gap-5 p-6 text-center"
		>
			<template v-if="phase === 'kicked'">
				<h1 class="font-display text-3xl font-extrabold text-paper">
					The host removed you
				</h1>
				<p class="text-paper/50">You can join again with the PIN.</p>
				<button
					class="rounded-2xl bg-ember px-7 py-3 font-display text-lg font-extrabold text-sunk"
					@click="router.replace('/join')"
				>
					Back to join
				</button>
			</template>

			<template v-else-if="phase === 'lobby'">
				<p class="font-mono text-[11px] uppercase tracking-[0.28em] text-accent">
					PIN {{ player.pin }}
				</p>
				<h1 class="font-display text-5xl font-extrabold text-paper">You're in</h1>
				<p class="max-w-xs text-paper/50">
					Find your name on the big screen. The host starts when everyone's here.
				</p>
				<p class="font-mono text-sm tabular-nums text-paper/40">
					{{ participants.length }} in the lobby
				</p>
			</template>

			<template v-else-if="phase === 'get_ready'">
				<p class="font-mono text-[11px] uppercase tracking-[0.28em] text-paper/40">
					Question {{ (qIndex ?? 0) + 1 }} of {{ total }}
				</p>
				<h1 class="max-w-md font-display text-2xl font-bold leading-snug text-paper">
					{{ questionText }}
				</h1>
				<DrainRing
					:percent="timerPercent"
					:seconds="Math.ceil(remaining)"
					:size="132"
					color="rgb(var(--accent))"
				/>
				<p class="text-paper/50">Read it. Answers land in a second.</p>
			</template>

			<template v-else-if="phase === 'locked'">
				<svg
					v-if="selected"
					class="h-28 w-28"
					:class="shapeFor(selected).svgFill"
					viewBox="0 0 24 24"
				>
					<path :d="shapeFor(selected).path" />
				</svg>
				<h1 class="font-display text-4xl font-extrabold text-paper">Locked in</h1>
				<p class="text-paper/50">Look up at the big screen.</p>
			</template>

			<template v-else-if="phase === 'result'">
				<div
					class="grid h-24 w-24 place-items-center rounded-full text-5xl text-sunk"
					:class="result.is_correct ? 'bg-lagoon' : 'bg-ember'"
				>
					{{ result.is_correct ? "✓" : "✕" }}
				</div>
				<h1 class="font-display text-4xl font-extrabold text-paper">
					{{ result.is_correct ? "Correct" : result.answered ? "Wrong" : "No answer" }}
				</h1>
				<p v-if="result.points" class="font-mono text-2xl font-bold text-accent">
					+{{ result.points }}
				</p>
				<p v-if="result.streak > 1" class="text-paper/60">
					{{ result.streak }} in a row 🔥
				</p>
				<p class="font-mono text-xs uppercase tracking-[0.2em] text-paper/40">
					Rank {{ result.rank }} · {{ result.score }} pts
				</p>
				<div
					v-if="explainer"
					class="mt-2 flex w-full max-w-xs flex-col gap-3 rounded-2xl border border-haze bg-dusk p-4 text-left"
				>
					<img
						v-if="explainer.image"
						:src="explainer.image"
						alt=""
						class="max-h-40 w-full rounded-xl object-contain"
					/>
					<p v-if="explainer.text" class="whitespace-pre-line text-sm text-paper/75">
						{{ explainer.text }}
					</p>
				</div>
				<ul class="mt-2 w-full max-w-xs text-left">
					<li
						v-for="(entry, index) in result.top_5"
						:key="entry.nickname"
						class="flex items-center justify-between border-b border-haze py-2 text-sm"
						:class="
							entry.nickname === player.nickname
								? 'font-bold text-accent'
								: 'text-paper/60'
						"
					>
						<span class="flex items-center gap-2">
							<span class="w-4 font-mono text-xs tabular-nums opacity-60">{{
								index + 1
							}}</span>
							<AvatarPic :id="entry.avatar" :nickname="entry.nickname" :size="22" />
							{{ entry.nickname }}
						</span>
						<span class="font-mono tabular-nums">{{ entry.score }}</span>
					</li>
				</ul>
			</template>

			<template v-else-if="phase === 'podium'">
				<h1 class="font-display text-5xl font-extrabold text-paper">
					{{ myRank === 1 ? "You won" : `You finished #${myRank}` }}
				</h1>
				<p class="font-mono text-2xl font-bold text-accent">{{ score }} pts</p>
				<ul class="mt-2 w-full max-w-xs text-left">
					<li
						v-for="entry in leaderboard.slice(0, 5)"
						:key="entry.nickname"
						class="flex items-center justify-between border-b border-haze py-2"
						:class="
							entry.nickname === player.nickname
								? 'font-bold text-accent'
								: 'text-paper/60'
						"
					>
						<span class="flex items-center gap-2">
							<span class="w-4 font-mono text-xs tabular-nums opacity-60">{{
								entry.rank
							}}</span>
							<AvatarPic :id="entry.avatar" :nickname="entry.nickname" :size="22" />
							{{ entry.nickname }}
						</span>
						<span class="font-mono tabular-nums">{{ entry.score }}</span>
					</li>
				</ul>
				<button
					class="mt-3 rounded-full border border-haze px-5 py-2 text-sm text-paper/60 transition hover:border-ember hover:text-alert"
					@click="playAgain"
				>
					Back to join
				</button>
			</template>

			<template v-else>
				<p class="font-mono text-sm uppercase tracking-[0.22em] text-paper/40">
					Hang tight
				</p>
			</template>
		</main>
	</div>
</template>

<script setup>
import { computed, inject, onMounted, ref, watch } from "vue";
import { useRouter } from "vue-router";
import { call } from "@/api";
import { clearPlayer, loadPlayer } from "@/player";
import { optionOrder, readExplainer, shapeFor, useCountdown, useSessionRoom } from "@/game";
import AvatarPic from "@/components/AvatarPic.vue";
import DrainRing from "@/components/DrainRing.vue";
import ThemeButton from "@/components/ThemeButton.vue";
import { initSound, muted, playCue, toggleMute } from "@/sound";

const router = useRouter();
const socket = inject("$socket");
const {
	remaining,
	total: windowSeconds,
	start: startCountdown,
	stop: stopCountdown,
} = useCountdown();

let stopRoom = () => {};

const player = ref(loadPlayer());
const phase = ref("lobby");
const participants = ref(player.value?.participants || []);
const question = ref(null);
const questionText = ref("");
const qIndex = ref(0);
const total = ref(0);
const selected = ref(null);
const score = ref(0);
const result = ref({});
const leaderboard = ref([]);
const myRank = ref(0);
const error = ref("");
const explainer = computed(() => readExplainer(result.value));

watch(
	() => Math.ceil(remaining.value),
	(secondsLeft) => {
		if (phase.value === "question" && secondsLeft > 0 && secondsLeft <= 5) playCue("tick");
	}
);

const timerPercent = computed(() =>
	windowSeconds.value ? (remaining.value / windowSeconds.value) * 100 : 0
);

const urgentColor = computed(() =>
	remaining.value <= 5 ? "rgb(var(--alert))" : "rgb(var(--ok))"
);

const orderedOptions = computed(() =>
	question.value ? optionOrder(question.value, player.value.token) : []
);

// Nothing left to follow once the host removes the player, so the room goes too:
// its resync watchdog would otherwise keep asking for a session we are out of.
function showKicked() {
	stopRoom();
	clearPlayer();
	stopCountdown();
	phase.value = "kicked";
}

function onSessionEvent(message) {
	if (message.type === "lobby_update") {
		participants.value = message.participants;
	} else if (message.type === "kicked" && message.participant === player.value.participant) {
		showKicked();
	} else if (message.type === "get_ready") {
		showGetReady(message.question_text, message.q_index, message.total, message.seconds);
	} else if (message.type === "question") {
		showQuestion(message, message.window_ms / 1000);
	} else if (message.type === "question_closed") {
		showResult(message);
	} else if (message.type === "podium") {
		showPodium(message.leaderboard);
	} else if (message.type === "session_ended") {
		phase.value = "waiting";
	}
}

function showGetReady(text, index, questionTotal, seconds) {
	questionText.value = text;
	qIndex.value = index;
	total.value = questionTotal;
	phase.value = "get_ready";
	startCountdown(seconds);
}

function showQuestion(payload, remainingSeconds) {
	question.value = payload;
	qIndex.value = payload.q_index;
	total.value = payload.total;
	selected.value = null;
	error.value = "";
	phase.value = "question";
	startCountdown(remainingSeconds);
}

async function showResult(closedMessage) {
	stopCountdown();
	result.value = await call("quizzly.api.get_result", {
		pin: player.value.pin,
		token: player.value.token,
		question_row: closedMessage.question_row,
	});
	score.value = result.value.score;
	phase.value = "result";
	playCue(result.value.is_correct ? "correct" : "wrong");
}

function showPodium(entries) {
	stopCountdown();
	leaderboard.value = entries || [];
	myRank.value =
		leaderboard.value.find((entry) => entry.nickname === player.value.nickname)?.rank || 0;
	phase.value = "podium";
	playCue("podium");
}

async function answer(optionId) {
	selected.value = optionId;
	phase.value = "locked";
	stopCountdown();
	playCue("submit");
	try {
		await call("quizzly.api.submit_answer", {
			pin: player.value.pin,
			token: player.value.token,
			question_row: question.value.question_row,
			selected_option: optionId,
		});
	} catch (e) {
		error.value = e.messages?.[0] || e.message;
		selected.value = null;
	}
}

async function restore() {
	const state = await call("quizzly.api.get_state", {
		pin: player.value.pin,
		token: player.value.token,
	});
	score.value = state.score;
	if (state.status === "Lobby") {
		participants.value = state.participants;
		phase.value = "lobby";
		return;
	}
	if (state.status === "Ended") {
		showPodium(state.leaderboard);
		return;
	}
	if (state.phase === "get_ready") {
		showGetReady(
			state.question.question_text,
			state.q_index,
			state.total,
			state.remaining_seconds
		);
	} else if (state.phase === "question") {
		showQuestion(state.question, state.remaining_seconds);
		if (state.answered) {
			phase.value = "locked";
			stopCountdown();
		}
	} else if (state.phase === "closed") {
		await showResult({ question_row: state.question.question_row });
	} else {
		phase.value = "waiting";
	}
}

onMounted(() => {
	initSound("player");
	if (!player.value) {
		router.replace("/join");
		return;
	}
	stopRoom = useSessionRoom(socket, player.value.pin, onSessionEvent, safeRestore);
});

async function safeRestore() {
	try {
		await restore();
	} catch (e) {
		// The kick and cancel paths normally arrive over realtime. When that is down the
		// resync watchdog is what learns about them, and retrying a session the player is
		// no longer in just 404s every 20s until the tab closes.
		if (e.exc_type === "DoesNotExistError") {
			clearPlayer();
			router.replace("/join");
			return;
		}
		if (e.exc_type === "PermissionError") {
			showKicked();
			return;
		}
		error.value = e.messages?.[0] || e.message;
	}
}

async function leave() {
	try {
		await call("quizzly.api.leave_session", {
			pin: player.value.pin,
			token: player.value.token,
		});
	} catch {
		// leaving anyway
	}
	playAgain();
}

function playAgain() {
	clearPlayer();
	router.replace("/join");
}
</script>
