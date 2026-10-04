<template>
	<n-card
		class="soc-segmented-panel"
		size="small"
		:segmented="{ content: true, footer: true }"
		:header-style="`${SURFACE}; padding-left: 12px; padding-right: 12px`"
		:content-style="flush ? 'padding: 0' : 'padding: 12px'"
		:footer-style="`${SURFACE}; padding: 10px 12px`"
	>
		<template #header>
			<div class="flex min-w-0 items-baseline gap-2">
				<span :class="SECTION_LABEL" class="shrink-0 whitespace-nowrap">{{ title }}</span>
				<span v-if="caption" class="text-tertiary text-2xs min-w-0 truncate font-mono">{{ caption }}</span>
			</div>
		</template>
		<template v-if="$slots.actions" #header-extra>
			<div class="flex flex-wrap items-center gap-2">
				<slot name="actions" />
			</div>
		</template>
		<slot />
		<template v-if="$slots.footer" #footer>
			<slot name="footer" />
		</template>
	</n-card>
</template>

<script setup lang="ts">
// A SOC Management section as a Naive segmented card: header, body and an optional
// footer (the save bar of an editor) each in their own band, split by hairlines. Same
// title voice as SocPanel; used where a section has something to commit.
import { NCard } from "naive-ui"
import { SECTION_LABEL } from "@/components/common/section-label"

const { title, caption, flush = false } = defineProps<{ title: string; caption?: string; flush?: boolean }>()

/** Header and footer bands sit on the secondary surface, with the page's 12px gutter — like SocPanel's header strip. */
const SURFACE = "background-color: var(--bg-secondary-color)"
</script>

<!-- Unscoped: these reach into n-card's own header, which a scoped selector does not. -->
<style>
.soc-segmented-panel > .n-card-header {
	min-height: 40px;
	padding-top: 8px;
	padding-bottom: 8px;
	justify-content: space-between;
}

/* Let a long caption truncate instead of pushing the title out of the padding.
   naive-override.scss pins every card title to min-width: auto !important; this
   panel's caption is the one thing allowed to give way, so it opts out here only. */
.n-card.soc-segmented-panel > .n-card-header > .n-card-header__main {
	min-width: 0 !important;
}
</style>
