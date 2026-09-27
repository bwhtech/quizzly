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
				Live quiz
			</p>
			<h1 class="font-display text-6xl font-extrabold leading-none text-paper">TriviaTap</h1>
			<p class="mt-3 text-paper/50">
				Type the PIN on the big screen, pick a face, and you're in.
			</p>

			<form class="mt-9 flex flex-col gap-6" @submit.prevent="join">
				<label class="flex flex-col gap-2">
					<span class="font-mono text-[11px] uppercase tracking-[0.22em] text-paper/45">
						Game PIN
					</span>
					<input
						v-model="pin"
						class="w-full rounded-2xl border border-haze bg-dusk py-4 text-center font-mono text-4xl font-bold tracking-[0.18em] text-paper placeholder:text-paper/20 focus:border-ember"
						placeholder="000000"
						inputmode="numeric"
						maxlength="6"
						autocomplete="off"
					/>
				</label>

				<label class="flex flex-col gap-2">
					<span class="font-mono text-[11px] uppercase tracking-[0.22em] text-paper/45">
						Nickname
					</span>
					<input
						v-model="nickname"
						class="w-full rounded-2xl border border-haze bg-dusk px-4 py-3.5 text-lg font-medium text-paper placeholder:text-paper/25 focus:border-ember"
						placeholder="Your name"
						maxlength="20"
						autocomplete="off"
					/>
					<span class="flex flex-wrap items-center gap-2 pt-1">
						<button
							v-for="suggestion in suggestions"
							:key="suggestion"
							type="button"
							class="rounded-full border border-haze px-3 py-1 text-sm text-paper/70 transition hover:border-lagoon hover:text-ok"
							@click="nickname = suggestion"
						>
							{{ suggestion }}
						</button>
						<button
							type="button"
							class="rounded-full border border-haze px-3 py-1 text-sm text-paper/45 transition hover:border-paper hover:text-paper"
							@click="suggestions = suggestNicknames()"
						>
							↻ More
						</button>
					</span>
				</label>

				<div class="flex flex-col gap-3">
					<span class="font-mono text-[11px] uppercase tracking-[0.22em] text-paper/45">
						Your face
					</span>
					<!-- The bleed lives on the wrapper so the scroller's 50% end padding,
					     which is what lets the first and last face reach the centre line,
					     measures against the full-bleed width. -->
					<div class="-mx-5">
						<div
							ref="scroller"
							class="no-scrollbar flex snap-x snap-mandatory gap-1 overflow-x-auto px-[calc(50%-22px)] py-1.5 motion-safe:scroll-smooth"
							@scroll="queuePick"
						>
							<!-- Only the face inside scales, so picking never reflows the row. -->
							<button
								v-for="option in avatars"
								:key="option.id"
								:data-avatar="option.id"
								type="button"
								class="shrink-0 snap-center"
								:aria-label="option.id"
								:aria-pressed="avatar === option.id"
								@click="select(option.id)"
							>
								<span
									class="block rounded-full p-0.5 transition duration-200"
									:class="
										avatar === option.id
											? 'bg-gold ring-2 ring-gold'
											: 'scale-[0.62] opacity-55 hover:opacity-100'
									"
								>
									<AvatarPic :id="option.id" :size="40" />
								</span>
							</button>
						</div>
					</div>
				</div>

				<button
					type="submit"
					class="rounded-2xl bg-ember py-4 font-display text-xl font-extrabold text-sunk transition hover:brightness-110 disabled:opacity-50"
					:disabled="joining"
				>
					{{ joining ? "Joining…" : "Join game" }}
				</button>
				<p v-if="error" class="text-center text-sm text-alert">
					{{ error }}
				</p>
			</form>
		</div>
	</div>
</template>

<script setup>
import { nextTick, onMounted, ref } from "vue";
import { useRoute, useRouter } from "vue-router";
import { call } from "@/api";
import { savePlayer } from "@/player";
import { avatars, randomAvatar } from "@/avatars";
import { suggestNicknames } from "@/nicknames";
import { SHAPES } from "@/game";
import AvatarPic from "@/components/AvatarPic.vue";
import ThemeButton from "@/components/ThemeButton.vue";

const route = useRoute();
const router = useRouter();

const pin = ref(route.query.pin || "");
const nickname = ref("");
const avatar = ref(randomAvatar());
const suggestions = ref(suggestNicknames());
const joining = ref(false);
const error = ref("");
const scroller = ref(null);

const centerSelected = (behavior) =>
	scroller.value
		?.querySelector(`[data-avatar="${avatar.value}"]`)
		?.scrollIntoView({ inline: "center", block: "nearest", behavior });

function select(id) {
	avatar.value = id;
	nextTick(() => centerSelected("smooth"));
}

// The highlight stays put and the faces move under it, so the pick is whatever
// the scroll parks in the centre. Snapping keeps it off the gaps between faces.
function pickCentered() {
	const row = scroller.value;
	if (!row) return;
	const center = row.getBoundingClientRect().left + row.clientWidth / 2;
	let closest = null;
	let smallest = Infinity;
	for (const slot of row.children) {
		const box = slot.getBoundingClientRect();
		const distance = Math.abs(box.left + box.width / 2 - center);
		if (distance < smallest) {
			smallest = distance;
			closest = slot;
		}
	}
	if (closest) avatar.value = closest.dataset.avatar;
}

let pickPending = false;
function queuePick() {
	if (pickPending) return;
	pickPending = true;
	requestAnimationFrame(() => {
		pickPending = false;
		pickCentered();
	});
}

// The opening pick is random, so it lands anywhere in the roster.
onMounted(() => centerSelected("instant"));

async function join() {
	error.value = "";
	joining.value = true;
	try {
		const result = await call("trivia_tap.api.join_session", {
			pin: pin.value.trim(),
			nickname: nickname.value.trim(),
			avatar: avatar.value,
		});
		savePlayer(result);
		router.push("/play");
	} catch (e) {
		error.value = e.messages?.[0] || e.message;
	} finally {
		joining.value = false;
	}
}
</script>
