<template>
	<div class="kpi-tile bg-default flex min-h-28 flex-col justify-between gap-2 p-4" :data-testid="testId">
		<div class="flex items-center justify-between gap-2">
			<span :class="SECTION_LABEL">{{ label }}</span>
			<n-tooltip v-if="help" placement="top" style="max-width: 300px">
				<template #trigger>
					<Icon name="carbon:information" :size="14" class="text-tertiary cursor-help" />
				</template>
				{{ help }}
			</n-tooltip>
		</div>
		<div class="flex flex-wrap items-baseline gap-x-2 gap-y-1">
			<span
				class="kpi-value text-3xl leading-none font-semibold"
				:style="{ color: valueColor }"
				data-testid="kpi-value"
			>
				{{ value }}
			</span>
			<DeltaChip :delta />
		</div>
		<span v-if="hint" class="text-tertiary truncate text-xs">{{ hint }}</span>
	</div>
</template>

<script setup lang="ts">
// A stat tile: label · value · optional delta vs the previous period · optional hint.
// The value keeps proportional figures (it stands alone); colour only when the value
// *is* a status — an SLA rate, a breach count — never as decoration.
import type { Delta, Tone } from "../utils"
import { NTooltip } from "naive-ui"
import { computed } from "vue"
import Icon from "@/components/common/Icon.vue"
import { SECTION_LABEL } from "@/components/common/section-label"
import { TONE_COLOR } from "../utils"
import DeltaChip from "./DeltaChip.vue"

const {
	label,
	value,
	hint,
	help,
	delta = null,
	tone,
	testId
} = defineProps<{
	label: string
	value: string
	hint?: string
	help?: string
	delta?: Delta | null
	/** Colours the value; omit for a plain (default ink) figure. */
	tone?: Tone
	testId?: string
}>()

const valueColor = computed(() => (tone && tone !== "neutral" ? TONE_COLOR[tone] : undefined))
</script>
