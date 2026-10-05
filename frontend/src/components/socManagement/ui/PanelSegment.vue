<template>
	<section class="panel-segment flex flex-col">
		<header class="border-default flex min-h-10 flex-wrap items-center justify-between gap-2 border-b px-3 py-2">
			<div class="flex min-w-0 items-baseline gap-2">
				<span :class="SECTION_LABEL" class="shrink-0 whitespace-nowrap">{{ title }}</span>
				<span v-if="caption" class="text-tertiary text-2xs min-w-0 truncate font-mono">{{ caption }}</span>
			</div>
			<div v-if="$slots.actions" class="flex flex-wrap items-center gap-2">
				<slot name="actions" />
			</div>
		</header>
		<div :class="{ 'p-3': !flush }">
			<slot />
		</div>
		<footer
			v-if="$slots.footer"
			class="bg-secondary border-default flex flex-wrap items-center justify-between gap-3 border-t px-3 py-2.5"
		>
			<slot name="footer" />
		</footer>
	</section>
</template>

<script setup lang="ts">
// One segment of a segmented surface (the SLA Policies editor): a header strip, a body
// and, when there is something to commit, a footer band for the save bar. It has no
// box of its own — the surface it sits in draws the outline and the hairlines between
// segments, so several segments read as one attached piece rather than separate cards.
import { SECTION_LABEL } from "@/components/common/section-label"

const { title, caption, flush = false } = defineProps<{ title: string; caption?: string; flush?: boolean }>()
</script>
