<template>
	<div class="relative">
		<input
			v-model="value"
			class="!pr-12"
			:type="shown ? 'text' : 'password'"
			v-bind="$attrs"
		/>
		<button
			type="button"
			class="absolute inset-y-0 right-0 flex w-12 items-center justify-center text-paper/45 transition hover:text-paper"
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
