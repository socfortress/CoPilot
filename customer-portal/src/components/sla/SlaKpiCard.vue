<template>
	<article
		class="bg-default border-default flex min-w-0 flex-col gap-3 rounded-lg border p-4"
		:data-testid="`sla-kpi-${kpi.key}`"
	>
		<header class="flex items-center justify-between gap-2">
			<h3 class="text-secondary text-sm font-medium">{{ kpi.title }}</h3>
			<span
				v-if="kpi.delta.points !== null"
				class="flex items-center gap-0.5 font-mono text-xs tabular-nums"
				:class="deltaClass"
				:title="`${deltaText} points vs the previous period`"
				data-testid="sla-kpi-delta"
			>
				<Icon v-if="kpi.delta.direction === 'up'" name="carbon:arrow-up" :size="12" />
				<Icon v-else-if="kpi.delta.direction === 'down'" name="carbon:arrow-down" :size="12" />
				<Icon v-else name="carbon:subtract" :size="12" />
				{{ deltaText }}
			</span>
		</header>

		<div class="flex items-baseline gap-2">
			<span
				class="font-display text-3xl leading-none font-semibold tabular-nums"
				:class="rateClass"
				data-testid="sla-kpi-rate"
			>
				{{ formatRate(kpi.rate) }}
			</span>
			<span class="text-tertiary text-xs">{{ kpi.caption }}</span>
		</div>

		<!-- The rate as a bar: the share kept, over the clocks that have an outcome. -->
		<div class="bg-body h-1 w-full overflow-hidden rounded-full" role="presentation">
			<div
				class="h-full rounded-full transition-all duration-500 ease-out motion-reduce:transition-none"
				:class="barClass"
				:style="{ width: `${kpi.rate ?? 0}%` }"
			/>
		</div>

		<footer class="text-tertiary flex items-center justify-between gap-2 font-mono text-xs tabular-nums">
			<span data-testid="sla-kpi-count">{{ kpi.decided ? `${kpi.met} of ${kpi.decided} on target` : "no outcome yet" }}</span>
			<span :title="kpi.medianLabel" data-testid="sla-kpi-median">
				<Icon name="carbon:time" :size="12" class="mr-1 inline-block align-[-1px]" />
				{{ kpi.median }}
			</span>
		</footer>
	</article>
</template>

<script setup lang="ts">
import type { SlaKpi } from "./sla"
import { computed } from "vue"
import Icon from "@/components/common/Icon.vue"
import { bgClass, textClass } from "@/components/overview/shared/status"
import { formatRate, rateTone } from "./sla"

const { kpi } = defineProps<{
	kpi: SlaKpi
}>()

const tone = computed(() => rateTone(kpi.rate))
const rateClass = computed(() => (tone.value === "neutral" ? "text-tertiary" : textClass(tone.value)))
const barClass = computed(() => bgClass(tone.value))
const deltaText = computed(() => {
	const points = kpi.delta.points ?? 0
	return `${points > 0 ? "+" : ""}${points.toFixed(1)}`
})
const deltaClass = computed(() => {
	if (kpi.delta.direction === "up") return "text-success"
	return kpi.delta.direction === "down" ? "text-error" : "text-tertiary"
})
</script>
