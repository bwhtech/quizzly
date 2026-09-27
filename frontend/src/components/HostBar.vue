<template>
	<header
		class="flex shrink-0 flex-wrap items-center gap-x-4 gap-y-2 border-b border-haze px-4 py-3 sm:gap-x-5 sm:px-6"
	>
		<RouterLink
			class="flex items-center gap-2 font-display text-lg font-extrabold text-paper"
			to="/host"
		>
			<img alt="" class="size-7 rounded-md" :src="logoUrl" />
			TriviaTap
		</RouterLink>
		<nav class="flex items-center gap-2">
			<RouterLink class="ctl" :data-on="isHosting" to="/host">Host</RouterLink>
			<RouterLink class="ctl" :data-on="isAuthoring" to="/host/quizzes">Quizzes</RouterLink>
		</nav>
		<span class="ml-auto flex items-center gap-4">
			<ThemeButton class="ctl" />
			<span class="hidden truncate font-mono text-xs text-paper/40 sm:inline">{{
				user
			}}</span>
			<button class="font-mono text-xs text-paper/40 hover:text-paper" @click="logout">
				Logout
			</button>
		</span>
	</header>
</template>

<script setup>
import { computed } from "vue";
import { useRoute } from "vue-router";
import { call } from "@/api";
import ThemeButton from "@/components/ThemeButton.vue";

const logoUrl = "/assets/trivia_tap/images/trivia-tap-logo.png";

const route = useRoute();
const user = window.session_user;

const isHosting = computed(() => route.path === "/host");
const isAuthoring = computed(() => route.path.startsWith("/host/quizzes"));

async function logout() {
	await call("logout");
	window.location.href = "/trivia-tap/join";
}
</script>
