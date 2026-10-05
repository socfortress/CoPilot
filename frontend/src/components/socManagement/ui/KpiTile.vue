<template>
	<div class="kpi-tile bg-default flex min-h-28 flex-col justify-between gap-2 p-4" :data-testid="testId">
		<div class="flex min-h-6 items-center justify-between gap-2">
			<span :class="SECTION_LABEL">{{ label }}</span>
			<div class="flex items-center gap-1">
				<RouterLink v-if="to" v-slot="{ href, navigate }" :to custom>
					<n-button
						tag="a"
						:href
						size="tiny"
						secondary
						class="kpi-link"
						:aria-label="linkLabel"
						:data-testid="testId ? `${testId}-link` : undefined"
						@click="navigate"
					>
						View
						<template #icon><Icon name="carbon:arrow-up-right" :size="12" /></template>
					</n-button>
				</RouterLink>
				<n-tooltip v-if="help" placement="top" style="max-width: 300px">
					<template #trigger>
						<Icon name="carbon:information" :size="14" class="text-tertiary cursor-help" />
					</template>
					{{ help }}
				</n-tooltip>
			</div>
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
// *is* a status — an SLA rate, a breach count — never as decoration. A tile with a `to`
// gets a "View" button to the page behind its figure, shown on hover or keyboard focus.
import type { RouteLocationRaw } from "vue-router"
import type { Delta, Tone } from "../utils"
import { NButton, NTooltip } from "naive-ui"
import { computed } from "vue"
import { RouterLink } from "vue-router"
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
	testId,
	to,
	linkLabel
} = defineProps<{
	label: string
	value: string
	hint?: string
	help?: string
	delta?: Delta | null
	/** Colours the value; omit for a plain (default ink) figure. */
	tone?: Tone
	testId?: string
	/** The page behind the figure (the alerts list, the cases list…). */
	to?: RouteLocationRaw
	/** Accessible name of the "View" button, e.g. "Open the alerts list". */
	linkLabel?: string
}>()

const valueColor = computed(() => (tone && tone !== "neutral" ? TONE_COLOR[tone] : undefined))
</script>

<style scoped>
.kpi-link {
	opacity: 0;
	transition: opacity 0.15s var(--bezier-ease, ease);
}

.kpi-tile:hover .kpi-link,
.kpi-tile:focus-within .kpi-link {
	opacity: 1;
}

/* No hover on touch screens: keep it visible. */
@media (hover: none) {
	.kpi-link {
		opacity: 1;
	}
}
</style>
