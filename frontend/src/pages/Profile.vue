<template>
	<div class="flex h-full flex-col overflow-y-auto bg-night">
		<HostBar />
		<div class="mx-auto flex w-full max-w-2xl flex-1 flex-col gap-8 p-5 pb-20 sm:p-8 sm:pb-20">
			<div class="flex items-end justify-between gap-4">
				<div class="min-w-0">
					<p class="font-mono text-[11px] uppercase tracking-[0.28em] text-accent">
						Host
					</p>
					<h1 class="mt-2 font-display text-4xl font-extrabold text-paper sm:text-5xl">
						Your profile
					</h1>
					<p class="mt-2 truncate font-mono text-xs text-paper/40">{{ user }}</p>
				</div>
				<button class="ctl shrink-0 gap-2" @click="logout">
					<LucideLogOut class="size-4" />
					Log out
				</button>
			</div>

			<form
				class="flex flex-col gap-4 rounded-2xl border border-haze bg-dusk p-4 sm:p-5"
				@submit.prevent="saveName"
			>
				<h2 class="font-display text-xl font-bold text-paper">Name</h2>
				<div class="grid gap-4 sm:grid-cols-2">
					<label class="flex flex-col gap-2">
						<span class="font-mono text-xs text-paper/50">First name</span>
						<input
							v-model="firstName"
							class="field"
							autocomplete="given-name"
							required
						/>
					</label>
					<label class="flex flex-col gap-2">
						<span class="font-mono text-xs text-paper/50">Last name</span>
						<input v-model="lastName" class="field" autocomplete="family-name" />
					</label>
				</div>
				<div class="flex items-center gap-4">
					<button class="ctl ctl-go" :disabled="savingName">
						{{ savingName ? "Saving…" : "Save name" }}
					</button>
					<p
						v-if="nameNote"
						class="text-sm"
						:class="nameFailed ? 'text-alert' : 'text-ok'"
					>
						{{ nameNote }}
					</p>
				</div>
			</form>

			<form
				class="flex flex-col gap-4 rounded-2xl border border-haze bg-dusk p-4 sm:p-5"
				@submit.prevent="changePassword"
			>
				<h2 class="font-display text-xl font-bold text-paper">Password</h2>
				<!-- lets password managers tie the new password to this account -->
				<input :value="user" autocomplete="username" hidden />
				<div class="flex flex-col gap-2">
					<label class="font-mono text-xs text-paper/50" for="current-password"
						>Current password</label
					>
					<PasswordInput
						id="current-password"
						v-model="oldPassword"
						class="field"
						autocomplete="current-password"
						required
					/>
				</div>
				<div class="grid gap-4 sm:grid-cols-2">
					<div class="flex flex-col gap-2">
						<label class="font-mono text-xs text-paper/50" for="new-password"
							>New password</label
						>
						<PasswordInput
							id="new-password"
							v-model="newPassword"
							class="field"
							autocomplete="new-password"
							required
						/>
					</div>
					<div class="flex flex-col gap-2">
						<label class="font-mono text-xs text-paper/50" for="confirm-new-password"
							>Confirm new password</label
						>
						<PasswordInput
							id="confirm-new-password"
							v-model="confirmPassword"
							class="field"
							autocomplete="new-password"
							required
						/>
					</div>
				</div>
				<div class="flex items-center gap-4">
					<button class="ctl ctl-go" :disabled="savingPassword">
						{{ savingPassword ? "Changing…" : "Change password" }}
					</button>
					<p
						v-if="passwordNote"
						class="text-sm"
						:class="passwordFailed ? 'text-alert' : 'text-ok'"
					>
						{{ passwordNote }}
					</p>
				</div>
			</form>
		</div>
	</div>
</template>

<script setup>
import { onMounted, ref } from "vue";
import { useRoute, useRouter } from "vue-router";
import { call, errorText } from "@/api";
import { firstName as greetedName } from "@/host";
import HostBar from "@/components/HostBar.vue";
import PasswordInput from "@/components/PasswordInput.vue";

const route = useRoute();
const router = useRouter();
const user = window.session_user;

const firstName = ref("");
const lastName = ref("");
const savingName = ref(false);
const nameNote = ref("");
const nameFailed = ref(false);

const oldPassword = ref("");
const newPassword = ref("");
const confirmPassword = ref("");
const savingPassword = ref(false);
const passwordChanged = route.query.password === "changed";
const passwordNote = ref(passwordChanged ? "Password changed." : "");
const passwordFailed = ref(false);

onMounted(async () => {
	if (passwordChanged) router.replace({ query: {} });
	const profile = await call("frappe.client.get", { doctype: "User", name: user });
	firstName.value = profile.first_name || "";
	lastName.value = profile.last_name || "";
});

async function saveName() {
	savingName.value = true;
	try {
		await call("frappe.client.set_value", {
			doctype: "User",
			name: user,
			fieldname: { first_name: firstName.value, last_name: lastName.value },
		});
		greetedName.value = firstName.value;
		showNameNote("Saved.", false);
	} catch (e) {
		showNameNote(errorText(e), true);
	} finally {
		savingName.value = false;
	}
}

async function changePassword() {
	if (newPassword.value !== confirmPassword.value) {
		showPasswordNote("Passwords do not match.", true);
		return;
	}
	savingPassword.value = true;
	try {
		await call("trivia_tap.auth.change_password", {
			old_password: oldPassword.value,
			new_password: newPassword.value,
		});
		// frappe starts a new session, so the CSRF token in this page is stale now
		window.location.href = "/trivia-tap/host/profile?password=changed";
	} catch (e) {
		showPasswordNote(errorText(e), true);
		savingPassword.value = false;
	}
}

async function logout() {
	await call("logout");
	window.location.href = "/trivia-tap/join";
}

function showNameNote(text, failed) {
	nameNote.value = text;
	nameFailed.value = failed;
}

function showPasswordNote(text, failed) {
	passwordNote.value = text;
	passwordFailed.value = failed;
}
</script>
