<template>
	<div class="relative">
		<input
			v-model="value"
			class="w-full rounded-2xl border border-haze bg-dusk py-3.5 pl-4 pr-14 text-lg font-medium text-paper placeholder:text-paper/25 focus:border-ember focus:ring-0"
			:type="shown ? 'text' : 'password'"
			v-bind="$attrs"
		/>
		<button
			type="button"
			class="absolute inset-y-0 right-0 flex w-14 items-center justify-center text-paper/45 transition hover:text-paper"
			:aria-label="shown ? 'Hide password' : 'Show password'"
			:aria-pressed="shown"
			@click="shown = !shown"
		>
			<LucideEyeOff v-if="shown" class="size-5" />
			<LucideEye v-else class="size-5" />
		</button>
	</div>
</template>

<script setup>
import { ref } from "vue";

defineOptions({ inheritAttrs: false });

const value = defineModel({ type: String });
const shown = ref(false);
</script>
