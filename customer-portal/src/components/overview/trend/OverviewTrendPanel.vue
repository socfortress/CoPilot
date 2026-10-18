<template>
	<OverviewPanel
		title="Trend"
		icon="carbon:chart-line"
		:meta="`last ${rangeLabel}`"
		:loading="loading && !days"
		:error="!days ? error : null"
		data-testid="overview-trend"
		@retry="emit('retry')"
	>
		<template #actions>
			<n-radio-group
				:value="range"
				size="small"
				aria-label="Trend period"
				data-testid="overview-trend-range"
				@update:value="emit('update:range', $event)"
			>
				<n-radio-button
					v-for="item of TREND_RANGES"
					:key="item.key"
					:value="item.key"
					:data-testid="`overview-trend-range-${item.key}`"
				>
					{{ item.key }}
				</n-radio-button>
			</n-radio-group>
		</template>

		<template #skeleton>
			<div class="flex flex-col gap-4 p-5">
				<n-skeleton :height="40" :width="320" :sharp="false" />
				<n-skeleton :height="240" :sharp="false" />
			</div>
		</template>

		<div
			v-if="days"
			class="@container flex grow flex-col transition-opacity"
			:class="{ 'opacity-60': loading }"
			:aria-busy="loading || undefined"
		>
			<div class="flex flex-wrap items-end justify-between gap-x-6 gap-y-3 px-5 pt-4">
				<n-radio-group v-model:value="entity" size="small" aria-label="Trend of" data-testid="overview-trend-entity">
					<n-radio-button
						v-for="item of TREND_ENTITIES"
						:key="item.key"
						:value="item.key"
						:data-testid="`overview-trend-entity-${item.key}`"
					>
						{{ item.label }}
					</n-radio-button>
				</n-radio-group>

				<!-- The figures are the chart's legend: each sits beside its line's colour. -->
				<dl v-if="!entityError" class="grid grid-cols-3 gap-x-6" data-testid="overview-trend-totals">
					<div v-for="figure of figures" :key="figure.key" class="flex flex-col gap-0.5">
						<dt class="text-secondary flex items-center gap-1.5 text-xs" :title="figure.hint">
							<span
								v-if="figure.color"
								class="h-0.5 w-3 rounded-full"
								:style="{ backgroundColor: figure.color }"
								aria-hidden="true"
							/>
							{{ figure.label }}
						</dt>
						<dd
							class="font-mono text-xl leading-none font-semibold tabular-nums"
							:data-testid="`overview-trend-${figure.key}`"
						>
							{{ figure.value }}
						</dd>
					</div>
				</dl>
			</div>

			<PanelError v-if="entityError" :message="entityError" @retry="emit('retry')" />
			<PanelEmpty
				v-else-if="!totals.opened && !totals.closed"
				icon="carbon:chart-line"
				:text="`No ${entityNoun} opened or closed in the last ${rangeLabel}`"
				data-testid="overview-trend-empty"
			/>
			<template v-else>
				<div class="px-3 pt-2 pb-3">
					<OverviewTrendChart :days :entity />
				</div>

				<table class="sr-only" data-testid="overview-trend-table">
					<caption>
						{{
							`${entityLabel} opened and closed per day, last ${rangeLabel}`
						}}
					</caption>
					<thead>
						<tr>
							<th scope="col">Day</th>
							<th scope="col">Opened</th>
							<th scope="col">Closed</th>
						</tr>
					</thead>
					<tbody>
						<tr v-for="day of days" :key="day.day">
							<th scope="row">{{ dayTitle(day.day) }}</th>
							<td>{{ day[entity].opened }}</td>
							<td>{{ day[entity].closed }}</td>
						</tr>
					</tbody>
				</table>
			</template>
		</div>
	</OverviewPanel>
</template>

<script setup lang="ts">
import type { TrendDay, TrendEntity } from "./trend"
import type { OverviewTrend, OverviewTrendRange } from "@/types/portal"
import { NRadioButton, NRadioGroup, NSkeleton } from "naive-ui"
import { computed, ref } from "vue"
import { useThemeStore } from "@/stores/theme"
import OverviewPanel from "../shared/OverviewPanel.vue"
import PanelEmpty from "../shared/PanelEmpty.vue"
import PanelError from "../shared/PanelError.vue"
import OverviewTrendChart from "./OverviewTrendChart.vue"
import { dayTitle, formatNet, TREND_COLORS, TREND_ENTITIES, TREND_RANGES, trendTotals } from "./trend"

const { trend, days, range, loading, error } = defineProps<{
	trend: OverviewTrend | null
	/** `trend` summed into the viewer's days; `null` until the first answer. */
	days: TrendDay[] | null
	range: OverviewTrendRange
	loading: boolean
	/** The request's own failure. Each entity's failure travels in `trend`. */
	error: string | null
}>()

const emit = defineEmits<{
	(e: "update:range", value: OverviewTrendRange): void
	(e: "retry"): void
}>()

const themeStore = useThemeStore()
const entity = ref<TrendEntity>("alerts")

const rangeLabel = computed(() => TREND_RANGES.find(item => item.key === range)?.label ?? range)
const entityLabel = computed(() => TREND_ENTITIES.find(item => item.key === entity.value)?.label ?? "")
const entityNoun = computed(() => entityLabel.value.toLowerCase())
const entityError = computed(() => (entity.value === "alerts" ? trend?.alerts_error : trend?.cases_error) ?? null)
const totals = computed(() => trendTotals(days ?? [], entity.value))

const figures = computed(() => {
	const colors = TREND_COLORS[themeStore.isThemeDark ? "dark" : "light"]
	return [
		{ key: "opened", label: "Opened", value: String(totals.value.opened), color: colors.opened, hint: undefined },
		{ key: "closed", label: "Closed", value: String(totals.value.closed), color: colors.closed, hint: undefined },
		{
			key: "net",
			label: "Net",
			value: formatNet(totals.value.net),
			color: null,
			hint: "Opened minus closed: how much the period added to what is still open"
		}
	]
})
</script>
