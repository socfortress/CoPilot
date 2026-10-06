<template>
	<div class="flex flex-wrap items-center justify-between gap-x-4 gap-y-2" data-testid="uba-toolbar">
		<div class="flex flex-wrap items-center gap-2">
			<slot />
		</div>
		<p v-if="$slots.hint" class="text-tertiary m-0 flex max-w-xl items-start gap-1.5 text-xs leading-relaxed">
			<Icon name="carbon:information" :size="13" class="mt-0.5 shrink-0" />
			<span><slot name="hint" /></span>
		</p>
	</div>
</template>

<script setup lang="ts">
// The row above a UBA list: its controls on the left (no field labels: placeholders and icons say
// what they are), and a one-line note on the right when the list needs explaining.
import Icon from "@/components/common/Icon.vue"
</script>
