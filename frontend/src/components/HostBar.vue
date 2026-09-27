<template>
	<header
		class="flex shrink-0 items-center gap-x-4 border-b border-haze px-4 py-3 sm:gap-x-5 sm:px-6"
	>
		<RouterLink
			class="flex shrink-0 items-center gap-2 font-display text-lg font-extrabold text-paper"
			to="/host"
			aria-label="TriviaTap"
		>
			<img alt="" class="size-7 rounded-md" :src="logoUrl" />
			<span class="hidden sm:inline">TriviaTap</span>
		</RouterLink>
		<nav class="flex items-center gap-2">
			<RouterLink class="ctl" :data-on="isHosting" to="/host">Host</RouterLink>
			<RouterLink class="ctl" :data-on="isAuthoring" to="/host/quizzes">Quizzes</RouterLink>
		</nav>
		<RouterLink
			class="ctl ml-auto min-w-0 gap-1"
			:data-on="isProfile"
			to="/host/profile"
			title="Your profile"
		>
			<span class="truncate">Hi, {{ firstName }}</span>
		</RouterLink>
		<ThemeButton
			class="fixed bottom-4 right-4 z-20 flex size-11 items-center justify-center rounded-full border border-haze bg-dusk text-lg shadow-lg transition hover:border-paper"
		/>
	</header>
</template>

<script setup>
import { computed } from "vue";
import { useRoute } from "vue-router";
import { firstName } from "@/host";
import ThemeButton from "@/components/ThemeButton.vue";

const logoUrl = "/assets/trivia_tap/images/trivia-tap-logo.png";

const route = useRoute();

const isHosting = computed(() => route.path === "/host");
const isAuthoring = computed(() => route.path.startsWith("/host/quizzes"));
const isProfile = computed(() => route.path === "/host/profile");
</script>
