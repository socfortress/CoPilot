<template>
	<!--
		A labelled list of short values — indicators, process names, registry keys,
		mutexes.

		The label sits OUTSIDE the box and only the list is boxed, so the border
		delimits the items themselves rather than wrapping a whole panel: what is
		framed is what you can scroll. Rows are hairline-separated for the same
		reason — a run of lines without them reads as a paragraph, not as entries.

		Values are monospace because these are identifiers, not prose, and the list
		scrolls inside an n-scrollbar rather than clipping: a native bar only appears
		while scrolling on some platforms, which makes a cut-off list read as
		truncated content.
	-->
	<div class="flex flex-col gap-2">
		<span :class="SECTION_LABEL">
			{{ label }}
			<span class="text-tertiary normal-case">({{ items.length }})</span>
		</span>

		<div class="border-default rounded-lg border">
			<n-scrollbar :style="{ maxHeight }">
				<div class="divide-border flex flex-col divide-y">
					<template v-for="(value, index) of items" :key="`${index}-${value}`">
						<a
							v-if="link"
							:href="link(value)"
							target="_blank"
							rel="noopener noreferrer"
							class="hover:text-primary hover:bg-primary/5 px-3 py-2 font-mono text-xs break-all transition-colors"
						>
							{{ value }}
						</a>
						<span v-else class="text-secondary px-3 py-2 font-mono text-xs break-all">{{ value }}</span>
					</template>
					<div v-if="!items.length" class="text-tertiary px-3 py-4 text-xs">{{ emptyText }}</div>
				</div>
			</n-scrollbar>
		</div>
	</div>
</template>

<script setup lang="ts">
import { NScrollbar } from "naive-ui"
import { SECTION_LABEL } from "@/components/common/section-label"

withDefaults(
	defineProps<{
		label: string
		items: string[]
		/** When given, each value becomes a link to `link(value)`. */
		link?: (value: string) => string
		maxHeight?: string
		emptyText?: string
	}>(),
	{ maxHeight: "13rem", emptyText: "—" }
)
</script>
