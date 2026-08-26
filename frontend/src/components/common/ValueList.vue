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
		<!-- The label is optional: inside a collapse item the title already names the
		     list, and repeating it directly under itself is noise. -->
		<span v-if="label" :class="SECTION_LABEL">
			{{ label }}
			<span class="text-tertiary normal-case">({{ items.length }})</span>
		</span>

		<div class="border-default rounded-lg border">
			<n-scrollbar :style="{ maxHeight }">
				<div class="divide-border flex flex-col divide-y">
					<template v-for="(value, index) of items" :key="`${index}-${keyOf(value)}`">
						<a
							v-if="link && typeof value === 'string'"
							:href="link(value)"
							target="_blank"
							rel="noopener noreferrer"
							class="hover:text-primary hover:bg-primary/5 px-3 py-2 font-mono text-xs break-all transition-colors"
						>
							{{ value }}
						</a>
						<span
							v-else-if="typeof value === 'string'"
							class="text-secondary px-3 py-2 font-mono text-xs break-all"
						>
							{{ value }}
						</span>
						<!-- A row made of parts: each part is a different kind of fact (what it
						     is called, what it is, what identifies it), so each gets its own
						     weight instead of running together as one grey string. -->
						<span v-else class="flex flex-wrap items-baseline px-3 py-2 font-mono text-xs">
							<template v-for="(part, pi) of value" :key="pi">
								<span v-if="pi" class="text-tertiary/50 px-1.5 select-none">·</span>
								<span class="min-w-0 break-all" :class="PART_TONE[part.tone ?? 'muted']">
									{{ part.text }}
								</span>
							</template>
						</span>
					</template>
					<div v-if="!items.length" class="text-tertiary px-3 py-4 text-xs">{{ emptyText }}</div>
				</div>
			</n-scrollbar>
		</div>
	</div>
</template>

<script setup lang="ts">
import type { ValueListItem } from "@/components/common/value-list"
import { NScrollbar } from "naive-ui"
import { SECTION_LABEL } from "@/components/common/section-label"
import { PART_TONE } from "@/components/common/value-list"

withDefaults(
	defineProps<{
		/** Omit where the surrounding chrome already names the list. */
		label?: string
		/** A plain string per row, or an array of parts to style each fact apart. */
		items: ValueListItem[]
		/** When given, each value becomes a link to `link(value)`. Plain rows only. */
		link?: (value: string) => string
		maxHeight?: string
		emptyText?: string
	}>(),
	{ maxHeight: "13rem", emptyText: "—" }
)

/** Rows are keyed by index first; this only keeps the key readable in devtools. */
function keyOf(value: ValueListItem): string {
	return typeof value === "string" ? value : value.map(p => p.text).join("|")
}
</script>
