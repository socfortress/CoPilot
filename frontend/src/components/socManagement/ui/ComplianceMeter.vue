<template>
	<n-tooltip placement="top" :disabled="!compliance.decided">
		<template #trigger>
			<div
				class="compliance-meter flex cursor-help items-center gap-2"
				:class="{ 'min-w-28': !compact }"
				data-testid="compliance-meter"
			>
				<div
					class="meter-track relative h-1.5 grow overflow-hidden rounded-full"
					:style="{ backgroundColor: track }"
					role="meter"
					:aria-valuenow="compliance.rate ?? undefined"
					aria-valuemin="0"
					aria-valuemax="100"
					:aria-label="`${label}: ${formatRate(compliance.rate)}`"
				>
					<div
						class="meter-fill h-full rounded-full"
						:style="{ width: `${compliance.rate ?? 0}%`, backgroundColor: color }"
					/>
				</div>
				<span class="w-12 shrink-0 text-right font-mono text-xs tabular-nums" :style="{ color: textColor }">
					{{ formatRate(compliance.rate) }}
				</span>
			</div>
		</template>
		<div class="font-mono text-xs">
			<div>{{ label }}</div>
			<div class="text-secondary">{{ complianceSummary(compliance) }}</div>
		</div>
	</n-tooltip>
</template>

<script setup lang="ts">
// SLA compliance as a meter: the fill carries the status (good / warn / bad), the
// track is a wash of the same hue, and the percentage is always printed beside it —
// colour is never the only channel. "No outcome yet" reads as an em dash, not 0%.
import type { Compliance } from "@/types/soc-management"
import { NTooltip } from "naive-ui"
import { computed } from "vue"
import { complianceSummary, formatRate, rateTone, TONE_COLOR } from "../utils"

const {
	compliance,
	label = "Within SLA",
	compact = false
} = defineProps<{
	compliance: Compliance
	label?: string
	compact?: boolean
}>()

const tone = computed(() => rateTone(compliance.rate))
const color = computed(() => TONE_COLOR[tone.value])
const track = computed(() =>
	compliance.rate == null ? "var(--border-color)" : `color-mix(in srgb, ${color.value} 16%, transparent)`
)
const textColor = computed(() => (compliance.rate == null ? "var(--fg-tertiary-color)" : undefined))
</script>
