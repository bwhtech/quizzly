<template>
	<div class="relative flex h-full flex-col overflow-y-auto bg-night px-5 py-10">
		<ThemeButton
			class="absolute right-4 top-4 text-lg leading-none opacity-60 transition hover:opacity-100"
		/>
		<div class="m-auto w-full max-w-sm">
			<p
				class="mb-3 flex items-center gap-2 font-mono text-[11px] uppercase tracking-[0.28em] text-accent"
			>
				<svg class="h-3 w-3 fill-gold" viewBox="0 0 24 24">
					<path :d="SHAPES[1].path" />
				</svg>
				Host
			</p>
			<h1 class="font-display text-6xl font-extrabold leading-none text-paper">TriviaTap</h1>
			<p class="mt-3 text-paper/50">
				{{
					isSignUp
						? "Make an account, write a quiz, and share the link."
						: "Log in to write quizzes and host a game."
				}}
			</p>

			<div class="mt-9 grid grid-cols-2 gap-1 rounded-2xl border border-haze bg-dusk p-1">
				<button
					v-for="tab in TABS"
					:key="tab.mode"
					type="button"
					class="rounded-xl py-2.5 font-medium transition"
					:class="
						mode === tab.mode ? 'bg-haze text-paper' : 'text-paper/50 hover:text-paper'
					"
					@click="switchTo(tab.mode)"
				>
					{{ tab.label }}
				</button>
			</div>

			<form class="mt-6 flex flex-col gap-5" @submit.prevent="submit">
				<label v-if="isSignUp" class="flex flex-col gap-2">
					<span class="font-mono text-[11px] uppercase tracking-[0.22em] text-paper/45"
						>Your name</span
					>
					<input
						v-model="fullName"
						class="w-full rounded-2xl border border-haze bg-dusk px-4 py-3.5 text-lg font-medium text-paper placeholder:text-paper/25 focus:border-ember focus:ring-0"
						autocomplete="name"
						placeholder="Ada Lovelace"
						required
					/>
				</label>
				<label class="flex flex-col gap-2">
					<span class="font-mono text-[11px] uppercase tracking-[0.22em] text-paper/45"
						>Email</span
					>
					<input
						v-model="email"
						class="w-full rounded-2xl border border-haze bg-dusk px-4 py-3.5 text-lg font-medium text-paper placeholder:text-paper/25 focus:border-ember focus:ring-0"
						type="email"
						autocomplete="email"
						placeholder="you@school.org"
						required
					/>
				</label>
				<div class="flex flex-col gap-2">
					<span class="flex items-baseline justify-between">
						<label
							class="font-mono text-[11px] uppercase tracking-[0.22em] text-paper/45"
							for="password"
						>
							Password
						</label>
						<a
							v-if="!isSignUp"
							class="text-sm text-paper/45 hover:text-paper"
							href="/login#forgot"
						>
							Forgot?
						</a>
					</span>
					<input
						id="password"
						v-model="password"
						class="w-full rounded-2xl border border-haze bg-dusk px-4 py-3.5 text-lg font-medium text-paper placeholder:text-paper/25 focus:border-ember focus:ring-0"
						type="password"
						:autocomplete="isSignUp ? 'new-password' : 'current-password'"
						required
					/>
				</div>

				<button
					type="submit"
					class="mt-1 rounded-2xl bg-ember py-4 font-display text-xl font-extrabold text-sunk transition hover:brightness-110 disabled:opacity-50"
					:disabled="busy"
				>
					{{ busy ? "One moment…" : isSignUp ? "Create account" : "Log in" }}
				</button>
				<p v-if="error" class="text-center text-sm text-alert">{{ error }}</p>
			</form>

			<RouterLink
				class="mt-8 block text-center text-sm text-paper/45 hover:text-paper"
				to="/join"
			>
				Joining a game? Enter the PIN instead
			</RouterLink>
		</div>
	</div>
</template>

<script setup>
import { computed, ref } from "vue";
import { useRoute } from "vue-router";
import { call, errorText } from "@/api";
import { SHAPES } from "@/game";
import ThemeButton from "@/components/ThemeButton.vue";

const TABS = [
	{ mode: "login", label: "Log in" },
	{ mode: "signup", label: "Sign up" },
];

const route = useRoute();

const mode = ref(route.query.mode === "signup" ? "signup" : "login");
const fullName = ref("");
const email = ref("");
const password = ref("");
const busy = ref(false);
const error = ref("");

const isSignUp = computed(() => mode.value === "signup");

function switchTo(next) {
	mode.value = next;
	error.value = "";
}

async function submit() {
	error.value = "";
	busy.value = true;
	try {
		if (isSignUp.value) {
			await call("trivia_tap.auth.sign_up", {
				full_name: fullName.value,
				email: email.value,
				password: password.value,
			});
		} else {
			await call("login", { usr: email.value, pwd: password.value });
		}
		// the session user and CSRF token come from the server-rendered boot, so reload
		window.location.href = `/trivia-tap${redirectPath()}`;
	} catch (e) {
		error.value = errorText(e);
		busy.value = false;
	}
}

// only paths inside the SPA, so the link cannot bounce a fresh login off-site
function redirectPath() {
	const path = route.query.redirect;
	return typeof path === "string" && path.startsWith("/") && !path.startsWith("//")
		? path
		: "/host";
}
</script>
