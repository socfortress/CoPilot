<template>
	<!-- Total (with how it splits) first, then one cell per status: one strip, split by hairlines. -->
	<section
		class="bg-default border-default divide-border grid grid-cols-2 divide-y overflow-hidden rounded-lg border @3xl:grid-cols-5 @3xl:divide-x @3xl:divide-y-0"
		:aria-label="`${entity} by status`"
		data-testid="status-strip"
	>
		<div class="col-span-2 flex min-w-0 flex-col gap-2.5 px-4 py-3 @3xl:col-span-1" data-testid="stat-total">
			<span class="text-tertiary flex items-center gap-1.5 text-xs">
				<Icon :name="icon" :size="14" />
				Total {{ entity.toLowerCase() }}
			</span>
			<span
				class="font-display text-2xl leading-none font-semibold tabular-nums"
				data-testid="stat-value"
				v-text="formatCount(counts.total)"
			/>
			<StatusBar :segments />
		</div>

		<div
			v-for="segment of segments"
			:key="segment.key"
			class="border-border flex min-w-0 flex-col gap-2.5 px-4 py-3 @max-3xl:odd:border-l"
			:class="{ 'is-waiting': segment.key === 'pending_customer' && segment.value > 0 }"
			:data-testid="`stat-${segment.key}`"
		>
			<span class="text-tertiary flex min-w-0 items-center gap-1.5 text-xs whitespace-nowrap">
				<span class="size-2 shrink-0 rounded-full" :class="bgClass(segment.color)" aria-hidden="true" />
				<span class="truncate first-letter:uppercase">{{ segment.label }}</span>
			</span>
			<div class="flex items-baseline justify-between gap-2">
				<span
					class="font-display text-2xl leading-none font-semibold tabular-nums"
					:class="{ 'text-primary': segment.key === 'pending_customer' && segment.value > 0 }"
					data-testid="stat-value"
					v-text="formatCount(segment.value)"
				/>
				<span
					class="text-tertiary font-mono text-xs tabular-nums"
					data-testid="stat-share"
					v-text="share(segment.value)"
				/>
			</div>
		</div>
	</section>
</template>

<script setup lang="ts">
// The status counts above the alert and case lists, in the Overview's voice: the total
// with its split as a bar, then each status with its share. Colours are the shared
// status palette (overview/shared/status.ts), so "open" is the same blue here, in the
// lists and on the Overview. "Waiting on you" is lifted while it is not zero: it is the
// one count the customer acts on.
import type { StatusCounts } from "@/types/portal"
import { computed } from "vue"
import Icon from "@/components/common/Icon.vue"
import { workflowSegments } from "@/components/overview/posture/postureCells"
import { bgClass } from "@/components/overview/shared/status"
import StatusBar from "@/components/overview/shared/StatusBar.vue"

const { counts, entity, icon } = defineProps<{
	counts: StatusCounts
	/** "Alerts" or "Cases": names the strip and its total. */
	entity: string
	icon: string
}>()

const segments = computed(() => workflowSegments(counts))

function formatCount(value: number) {
	return value.toLocaleString("en-US")
}

/** The share of the total, as a whole percent; nothing when there is no total. */
function share(value: number) {
	return counts.total ? `${Math.round((value / counts.total) * 100)}%` : ""
}
</script>

<style scoped>
.is-waiting {
	background-color: rgb(var(--primary-color-rgb) / 0.06);
}
</style>
