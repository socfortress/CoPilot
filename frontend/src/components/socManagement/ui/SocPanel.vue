<template>
	<section class="soc-panel border-default bg-default flex flex-col overflow-hidden rounded-lg border">
		<header
			class="bg-secondary border-default flex min-h-10 flex-wrap items-center justify-between gap-2 border-b px-3 py-2"
		>
			<div class="flex min-w-0 items-baseline gap-2">
				<span :class="SECTION_LABEL">{{ title }}</span>
				<span v-if="caption" class="text-tertiary text-2xs truncate font-mono">{{ caption }}</span>
			</div>
			<div v-if="$slots.actions" class="flex flex-wrap items-center gap-2">
				<slot name="actions" />
			</div>
		</header>
		<div class="flex grow flex-col" :class="{ 'p-3': !flush }">
			<slot />
		</div>
	</section>
</template>

<script setup lang="ts">
// The one card every SOC Management section sits in: a hairline box with a
// section-label header strip — the same chrome as the WAF and File Analysis pages.
import { SECTION_LABEL } from "@/components/common/section-label"

const { title, caption, flush = false } = defineProps<{ title: string; caption?: string; flush?: boolean }>()
</script>
