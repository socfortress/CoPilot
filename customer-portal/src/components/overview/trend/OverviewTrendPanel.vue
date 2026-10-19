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
			<div class="flex flex-wrap items-center gap-2">
				<n-radio-group
					v-model:value="entity"
					size="small"
					aria-label="Trend of"
					data-testid="overview-trend-entity"
				>
					<n-radio-button
						v-for="item of TREND_ENTITIES"
						:key="item.key"
						:value="item.key"
						:data-testid="`overview-trend-entity-${item.key}`"
					>
						{{ item.label }}
					</n-radio-button>
				</n-radio-group>
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
			</div>
		</template>

		<template #skeleton>
			<div class="flex flex-col gap-4 p-5">
				<n-skeleton :height="56" :width="360" :sharp="false" />
				<n-skeleton :height="320" :sharp="false" />
			</div>
		</template>

		<div
			v-if="days"
			class="flex grow flex-col transition-opacity"
			:class="{ 'opacity-60': loading }"
			:aria-busy="loading || undefined"
		>
			<PanelError v-if="entityError" :message="entityError" @retry="emit('retry')" />

			<template v-else>
				<!--
					What is still open first, then how the period moved it (Net), then what
					arrived and what was closed, then the worst moment. The swatches are the
					chart's legend.
				-->
				<div class="flex flex-wrap items-end gap-x-8 gap-y-3 px-5 pt-4" data-testid="overview-trend-totals">
					<div
						class="flex min-w-36 flex-col gap-1"
						title="Not closed yet: open, in progress or waiting on you. The posture card above counts only those still open."
					>
						<span class="text-tertiary font-mono text-[10px] tracking-[0.14em] uppercase">Open · now</span>
						<span
							class="font-mono text-4xl leading-none font-semibold tracking-tight tabular-nums"
							data-testid="overview-trend-open"
						>
							{{ totals.open ?? "—" }}
						</span>
						<span class="text-secondary font-mono text-[11px]" data-testid="overview-trend-open-caption">
							{{ openCaption }}
						</span>
					</div>

					<dl class="flex flex-wrap gap-x-6 gap-y-2 pb-1">
						<div v-for="stat of stats" :key="stat.key" class="flex flex-col gap-1" :title="stat.hint">
							<dt
								class="text-tertiary flex items-center gap-1.5 font-mono text-[10px] tracking-widest uppercase"
							>
								<span
									v-if="stat.color"
									class="h-0.5 w-3 rounded-full"
									:style="{ backgroundColor: stat.color }"
									aria-hidden="true"
								/>
								{{ stat.label }}
							</dt>
							<dd class="flex items-baseline gap-1.5">
								<span
									class="font-mono text-lg leading-none font-medium tabular-nums"
									:class="stat.tone"
									:data-testid="`overview-trend-${stat.key}`"
								>
									{{ stat.value }}
								</span>
								<span v-if="stat.sub" class="text-tertiary font-mono text-[11px]">{{ stat.sub }}</span>
							</dd>
						</div>
					</dl>
				</div>

				<PanelEmpty
					v-if="quiet"
					icon="carbon:chart-line"
					:text="`No ${entityNoun} opened, closed or still open in the last ${rangeLabel}`"
					data-testid="overview-trend-empty"
				/>
				<template v-else>
					<div class="px-3 pt-2 pb-3">
						<OverviewTrendChart :days :entity />
					</div>

					<table class="sr-only" data-testid="overview-trend-table">
						<caption>
							{{
								`${entityLabel} still open at the end of each day, opened and closed, last ${rangeLabel}`
							}}
						</caption>
						<thead>
							<tr>
								<th scope="col">Day</th>
								<th scope="col">Open at day end</th>
								<th scope="col">Opened</th>
								<th scope="col">Closed</th>
							</tr>
						</thead>
						<tbody>
							<tr v-for="day of days" :key="day.day">
								<th scope="row">{{ dayTitle(day.day) }}</th>
								<td>{{ day[entity].open ?? "—" }}</td>
								<td>{{ day[entity].opened }}</td>
								<td>{{ day[entity].closed }}</td>
							</tr>
						</tbody>
					</table>
				</template>
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
import {
	dayLabel,
	dayTitle,
	formatNet,
	netWord,
	TREND_COLORS,
	TREND_ENTITIES,
	TREND_RANGES,
	trendPeak,
	trendTotals
} from "./trend"

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
const peak = computed(() => trendPeak(days ?? [], entity.value))

/** Nothing arrived, nothing was closed and nothing was waiting: an empty chart says nothing. */
const quiet = computed(
	() => !totals.value.opened && !totals.value.closed && !totals.value.open && !totals.value.openAtStart
)

const openCaption = computed(() => {
	const { open, openAtStart } = totals.value
	if (open === null) return "not known"
	const state = open > 0 ? "still open" : "all cleared"
	return openAtStart === null ? state : `${state} · was ${openAtStart}`
})

const stats = computed(() => {
	const colors = TREND_COLORS[themeStore.isThemeDark ? "dark" : "light"]
	const { net, opened, closed } = totals.value
	return [
		{
			key: "net",
			label: "Net",
			value: formatNet(net),
			sub: netWord(net),
			tone: net > 0 ? "text-warning" : net < 0 ? "text-success" : "",
			color: null,
			hint: "Opened minus closed in the period. The closed include items opened before it, so it can be negative."
		},
		{
			key: "opened",
			label: "Opened",
			value: String(opened),
			sub: "",
			tone: "",
			color: colors.opened,
			hint: undefined
		},
		{
			key: "closed",
			label: "Closed",
			value: String(closed),
			sub: "",
			tone: "",
			color: colors.closed,
			hint: undefined
		},
		{
			key: "peak",
			label: "Peak open",
			value: peak.value ? String(peak.value.open) : "—",
			sub: peak.value && peak.value.open > 0 ? dayLabel(peak.value.day) : "",
			tone: "",
			color: null,
			hint: "The most still open at the end of a day in the period"
		}
	]
})
</script>
