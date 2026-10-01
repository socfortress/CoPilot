<template>
	<div class="load-bars flex flex-col gap-3">
		<div class="flex flex-wrap items-center gap-4 text-xs" role="list" aria-label="Legend">
			<span class="text-secondary inline-flex items-center gap-1.5" role="listitem">
				<span class="inline-block size-2.5 rounded-sm" :style="{ backgroundColor: primary }" />
				Alerts
			</span>
			<span class="text-secondary inline-flex items-center gap-1.5" role="listitem">
				<span class="inline-block size-2.5 rounded-sm" :style="{ backgroundColor: secondary }" />
				Cases
			</span>
		</div>
		<n-empty v-if="!rows.length" :description="emptyText" class="py-4" />
		<ul v-else class="m-0 flex list-none flex-col gap-2 p-0">
			<li
				v-for="row of rows"
				:key="row.key"
				class="load-row grid items-center gap-3"
				:data-testid="`load-row-${row.key}`"
			>
				<span class="truncate text-sm" :title="row.label">
					<slot name="label" :row>{{ row.label }}</slot>
				</span>
				<n-tooltip placement="top">
					<template #trigger>
						<div
							class="bar-track flex h-3 items-center"
							:aria-label="`${row.label}: ${row.alerts} alerts, ${row.cases} cases`"
						>
							<span
								v-if="row.alerts"
								class="bar-segment h-full rounded-l-sm"
								:class="{ 'rounded-r-sm': !row.cases }"
								:style="{ width: `${(row.alerts / scale) * 100}%`, backgroundColor: primary }"
							/>
							<span
								v-if="row.cases"
								class="bar-segment h-full rounded-r-sm"
								:class="{ 'rounded-l-sm': !row.alerts, 'gap-left': row.alerts }"
								:style="{ width: `${(row.cases / scale) * 100}%`, backgroundColor: secondary }"
							/>
						</div>
					</template>
					<div class="font-mono text-xs">
						<div>{{ row.label }}</div>
						<div class="text-secondary">{{ row.alerts }} alerts · {{ row.cases }} cases</div>
					</div>
				</n-tooltip>
				<span class="w-12 text-right font-mono text-sm tabular-nums">{{ row.alerts + row.cases }}</span>
				<span class="flex w-28 justify-end gap-2 font-mono text-xs tabular-nums">
					<span
						class="inline-flex items-center gap-0.5"
						:style="{ color: row.at_risk ? TONE_COLOR.warn : 'var(--fg-tertiary-color)' }"
						:title="`${row.at_risk} at risk`"
					>
						<Icon name="carbon:time" :size="12" />
						{{ row.at_risk }}
					</span>
					<span
						class="inline-flex items-center gap-0.5"
						:style="{ color: row.breached ? TONE_COLOR.bad : 'var(--fg-tertiary-color)' }"
						:title="`${row.breached} past SLA`"
					>
						<Icon name="carbon:warning-filled" :size="12" />
						{{ row.breached }}
					</span>
				</span>
			</li>
		</ul>
	</div>
</template>

<script setup lang="ts">
// Open load as horizontal stacked bars (alerts | cases) on one shared scale, with the
// at-risk / past-SLA counts printed beside each — never left to colour alone. Bars cap
// at 12px thick with a 2px surface gap between the two segments.
import { NEmpty, NTooltip } from "naive-ui"
import { computed } from "vue"
import Icon from "@/components/common/Icon.vue"
import { useSocChartColors } from "../charts/chart-colors"
import { TONE_COLOR } from "../utils"

export interface LoadRow {
	key: string
	label: string
	alerts: number
	cases: number
	at_risk: number
	breached: number
}

const { rows, emptyText = "Nothing open" } = defineProps<{ rows: LoadRow[]; emptyText?: string }>()

const { primary, secondary } = useSocChartColors()
const scale = computed(() => Math.max(1, ...rows.map(row => row.alerts + row.cases)))
</script>

<style scoped>
.load-row {
	grid-template-columns: minmax(96px, 160px) minmax(0, 1fr) auto auto;
}

.gap-left {
	margin-left: 2px;
}
</style>
