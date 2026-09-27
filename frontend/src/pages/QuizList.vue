<template>
	<div class="flex h-full flex-col overflow-y-auto bg-night">
		<HostBar />
		<div class="mx-auto flex w-full max-w-2xl flex-1 flex-col gap-8 p-5 pb-20 sm:p-8 sm:pb-20">
			<div class="flex items-end justify-between gap-4">
				<div>
					<p class="font-mono text-[11px] uppercase tracking-[0.28em] text-accent">
						Host
					</p>
					<h1 class="mt-2 font-display text-4xl font-extrabold text-paper sm:text-5xl">
						Your quizzes
					</h1>
				</div>
				<RouterLink class="ctl ctl-go shrink-0 whitespace-nowrap" to="/host/quizzes/new">
					New quiz
				</RouterLink>
			</div>

			<p v-if="error" class="text-alert">{{ error }}</p>

			<div v-if="quizzes.length" class="flex flex-col gap-2">
				<div
					v-for="quiz in quizzes"
					:key="quiz.name"
					class="flex flex-wrap items-center gap-3 rounded-2xl border border-haze bg-dusk px-5 py-4 sm:gap-4"
				>
					<div class="min-w-0 flex-1 basis-full sm:basis-0">
						<p class="truncate font-display text-xl font-bold text-paper">
							{{ quiz.title }}
						</p>
						<p class="font-mono text-xs text-paper/40">
							{{ quiz.question_count }}
							{{ quiz.question_count === 1 ? "question" : "questions" }}
						</p>
					</div>
					<RouterLink class="ctl" :to="`/host/quizzes/${quiz.name}`">Edit</RouterLink>
					<button class="ctl" @click="remove(quiz)">Delete</button>
				</div>
			</div>
			<p v-else-if="loaded" class="text-paper/50">No quizzes yet. Make your first one.</p>
		</div>
	</div>
</template>

<script setup>
import { onMounted, ref } from "vue";
import { call, readError } from "@/api";
import { confirm } from "@/confirm";
import HostBar from "@/components/HostBar.vue";

const quizzes = ref([]);
const loaded = ref(false);
const error = ref("");

onMounted(load);

async function load() {
	try {
		quizzes.value = await call("trivia_tap.api.list_quizzes");
		loaded.value = true;
	} catch (e) {
		error.value = readError(e);
	}
}

async function remove(quiz) {
	if (!(await confirm(`Delete "${quiz.title}"?`, { action: "Delete", danger: true }))) return;
	error.value = "";
	try {
		// a played quiz is refused by the TT Session link, which is the rule we want anyway
		await call("frappe.client.delete", { doctype: "TT Quiz", name: quiz.name });
		await load();
	} catch (e) {
		// the framework's own link error names doctypes and links into Desk, which means
		// nothing to a host who never opens it
		error.value =
			e.exc_type === "LinkExistsError"
				? `"${quiz.title}" has been played, so it cannot be deleted.`
				: readError(e);
	}
}
</script>
