<template>
	<div
		class="risk-meter"
		:class="size === 'lg' ? 'flex min-w-36 flex-col gap-1.5' : 'inline-flex items-center gap-2'"
		role="meter"
		:aria-valuenow="Math.round(risk)"
		aria-valuemin="0"
		:aria-valuemax="scale"
		:aria-label="`Risk ${riskLabel(risk)}, alert at ${threshold}`"
		data-testid="risk-meter"
	>
		<div v-if="size === 'lg'" class="flex items-baseline justify-between gap-3">
			<span class="text-secondary font-mono text-[10px] tracking-widest uppercase">risk</span>
			<span
				class="font-mono text-3xl leading-none font-semibold tabular-nums"
				:class="RISK_TEXT_CLASS[tone]"
				data-testid="risk-meter-value"
			>
				{{ riskLabel(risk) }}
			</span>
		</div>
		<span
			v-else
			class="w-9 text-right font-mono text-sm font-semibold tabular-nums"
			:class="RISK_TEXT_CLASS[tone]"
			data-testid="risk-meter-value"
		>
			{{ riskLabel(risk) }}
		</span>

		<!-- The track runs to twice the threshold; the notch marks where an alert opens. -->
		<span
			class="track relative block overflow-hidden rounded-full"
			:class="size === 'lg' ? 'h-1.5 w-full' : 'h-1 w-14'"
		>
			<span
				class="absolute inset-y-0 left-0 rounded-full transition-[width] duration-500"
				:class="RISK_BG_CLASS[tone]"
				:style="{ width: `${fill}%` }"
			/>
			<span class="notch absolute inset-y-0 w-px" :style="{ left: '50%' }" />
		</span>
		<span v-if="size === 'lg'" class="text-tertiary flex justify-between font-mono text-[10px] tabular-nums">
			<span>0</span>
			<span>alert {{ threshold }}</span>
			<span>{{ scale }}</span>
		</span>
	</div>
</template>

<script setup lang="ts">
// A UBA risk score: the number, coloured by its band, over a thin track that runs to twice the
// customer's alert threshold, with a notch where an alert opens. `sm` sits in a table cell, `lg`
// is a drawer's headline figure. The colour always has the number beside it.
import { computed } from "vue"
import { RISK_BG_CLASS, RISK_TEXT_CLASS, riskLabel, riskTone } from "../utils"

const {
	risk,
	threshold = 100,
	size = "sm"
} = defineProps<{
	risk: number
	threshold?: number
	size?: "sm" | "lg"
}>()

const tone = computed(() => riskTone(risk, threshold))
const scale = computed(() => threshold * 2)
const fill = computed(() => Math.max(0, Math.min(100, (risk / scale.value) * 100)))
</script>

<style scoped>
.track {
	background-color: var(--hover-color);
}

.notch {
	background-color: var(--fg-secondary-color);
	opacity: 0.6;
}
</style>
