<template>
	<div class="flex flex-col gap-4">
		<n-alert v-if="result.note" type="warning" :bordered="false" size="small">{{ result.note }}</n-alert>

		<n-alert
			v-if="result.missing_fields?.length"
			type="warning"
			:bordered="false"
			size="small"
			title="Fields not found in this customer's data"
		>
			<span class="text-sm">
				<code v-for="(field, i) of result.missing_fields" :key="field">
					{{ field }}{{ i < result.missing_fields.length - 1 ? ", " : "" }}
				</code>
				— the rule may never match for this customer. Check for typos or a different field naming.
			</span>
		</n-alert>

		<!--
			Headline figures as one segmented strip: the 1px grid gaps let the container
			background show through as dividers, so the segments stay flush and separated
			however the grid wraps.
		-->
		<div class="border-default bg-border grid grid-cols-2 gap-px overflow-hidden rounded-lg border md:grid-cols-4">
			<div v-for="(tile, i) of statTiles" :key="i" class="bg-default flex flex-col gap-0.75 px-3.5 py-2.75">
				<span
					class="text-secondary text-3xs flex items-center gap-1.5 font-semibold tracking-[0.07em] whitespace-nowrap uppercase"
				>
					<Icon :name="tile.icon" :size="13" :style="{ color: tile.color }" />
					{{ tile.title }}
				</span>
				<span class="font-display text-[22px] leading-tight font-bold">{{ tile.value }}</span>
			</div>
		</div>

		<!-- volume over time -->
		<section
			v-if="result.per_bucket.length"
			class="border-default bg-default flex flex-col overflow-hidden rounded-lg border"
		>
			<header class="border-default bg-secondary flex flex-wrap items-center gap-2 border-b px-3 py-2.25">
				<Icon :name="ChartIcon" :size="15" class="text-secondary shrink-0" />
				<h4 class="text-xs font-semibold tracking-[0.02em]">
					Matches per {{ result.bucket_unit === "1h" ? "hour" : "day" }}
				</h4>
				<div
					class="text-secondary text-2xs [&_b]:text-default ms-auto flex items-center gap-1.5 font-mono [&_b]:font-semibold"
				>
					<span>
						peak
						<b>{{ fmt(bucketPeak) }}</b>
					</span>
					<span class="opacity-40">·</span>
					<span>
						avg
						<b>{{ fmt(bucketAvg) }}</b>
					</span>
					<span class="opacity-40">·</span>
					<span>{{ result.per_bucket.length }} buckets</span>
				</div>
			</header>
			<div class="p-3">
				<ChartColumn :labels="bucketLabels" :data="bucketData" height="260px" labels-datetime monochrome />
			</div>
		</section>

		<ThresholdSimulation
			v-if="result.mode === 'aggregation' && result.aggregation"
			:aggregation="result.aggregation"
			:range-label
		/>

		<!-- top values -->
		<section v-if="topFieldEntries.length" class="flex flex-col gap-2">
			<SectionHeading>Top values (from sampled events)</SectionHeading>
			<div class="grid grid-cols-1 gap-3 md:grid-cols-2">
				<div
					v-for="[field, values] of topFieldEntries"
					:key="field"
					class="border-default bg-default flex flex-col overflow-hidden rounded-lg border"
				>
					<header class="border-default bg-secondary flex items-center gap-2 border-b px-2.5 py-1.75">
						<Icon :name="FieldIcon" :size="13" class="text-secondary shrink-0" />
						<code
							class="text-default overflow-hidden bg-transparent p-0 font-mono text-[11.5px] font-semibold text-ellipsis whitespace-nowrap"
							:title="field"
						>
							{{ field }}
						</code>
						<span
							class="text-primary text-3xs ms-auto rounded-full bg-[rgba(var(--primary-color-rgb)/0.14)] px-1.75 py-0.25 font-mono font-semibold"
						>
							{{ values.length }}
						</span>
					</header>
					<div class="flex flex-col gap-1.5 p-2.5">
						<MeterRow
							v-for="(entry, i) of values"
							:key="i"
							:label="entry.value"
							:value="entry.count"
							:max="maxTopCount(values)"
						/>
					</div>
				</div>
			</div>
		</section>

		<!-- samples -->
		<section v-if="result.samples.length" class="mb-6 flex flex-col gap-2">
			<div class="flex flex-wrap items-center gap-2">
				<SectionHeading>Sample events ({{ result.samples.length }})</SectionHeading>
				<span class="text-secondary text-xs">click a row to inspect the full log</span>
			</div>
			<n-data-table
				:columns="sampleColumns"
				:data="result.samples"
				bordered
				size="small"
				:max-height="280"
				:row-props
				:scroll-x="Math.max(640, sampleColumns.length * 170)"
			/>
		</section>

		<n-empty
			v-else-if="!result.total_hits"
			description="No matching events in this window — the rule would not have fired."
			class="py-10"
		>
			<template #icon><Icon :name="EmptyIcon" :size="36" /></template>
		</n-empty>
	</div>
</template>

<script setup lang="ts">
import type { BacktestResponse, BacktestTopValue } from "@/types/copilot-searches"
import { NAlert, NDataTable, NEmpty } from "naive-ui"
import { computed, h } from "vue"
import ChartColumn from "@/components/common/charts/ChartColumn.vue"
import Icon from "@/components/common/Icon.vue"
import SectionHeading from "@/components/copilotSearches/SectionHeading.vue"
import { useThemeStore } from "@/stores/theme"
import { fmt } from "./format"
import MeterRow from "./MeterRow.vue"
import ThresholdSimulation from "./ThresholdSimulation.vue"

const { result, rangeLabel } = defineProps<{
	result: BacktestResponse
	/** Human look-back ("7d"), shown in the stat strip and the threshold captions. */
	rangeLabel: string
}>()

const emit = defineEmits<{
	(e: "inspect", event: Record<string, unknown>): void
}>()

const ChartIcon = "carbon:chart-column"
const FieldIcon = "carbon:data-vis-1"
const EmptyIcon = "carbon:search"

const themeStore = useThemeStore()

/** Aggregation mode swaps the fourth tile: estimated alerts matter more than the sample size. */
const statTiles = computed(() => {
	const style = themeStore.style
	const tiles = [
		{ title: "Total matches", value: fmt(result.total_hits), icon: "carbon:search", color: style["primary-color"] },
		{
			title: "Avg / day",
			value: String(result.per_day_avg),
			icon: "carbon:calendar",
			color: style["success-color"]
		},
		{ title: "Window", value: rangeLabel, icon: "carbon:time", color: style["fg-secondary-color"] }
	]

	if (result.mode === "aggregation") {
		tiles.push({
			title: "Est. alerts",
			value: fmt(result.aggregation?.estimated_alerts ?? 0),
			icon: "carbon:warning-alt",
			color: style["warning-color"]
		})
	} else {
		tiles.push({
			title: "Analyzed",
			value: fmt(result.fetched),
			icon: "carbon:list-checked",
			color: style["info-color"] || style["primary-color"]
		})
	}

	return tiles
})

const bucketLabels = computed(() => result.per_bucket.map(b => b.bucket))
const bucketData = computed(() => result.per_bucket.map(b => b.count))
const bucketPeak = computed(() => Math.max(0, ...bucketData.value))
const bucketAvg = computed(() => {
	const counts = bucketData.value
	return counts.length ? Math.round(counts.reduce((acc, n) => acc + n, 0) / counts.length) : 0
})

const topFieldEntries = computed<[string, BacktestTopValue[]][]>(() => Object.entries(result.top_fields || {}))

function maxTopCount(values: BacktestTopValue[]): number {
	return Math.max(1, ...values.map(v => v.count))
}

/** Six columns at most — beyond that the table scrolls further than it reads. */
const sampleColumns = computed(() => {
	const columns: any[] = (result.sample_fields || []).slice(0, 6).map(field => ({
		title: field,
		key: field,
		ellipsis: { tooltip: true },
		render: (row: Record<string, unknown>) => {
			const value = row[field]
			return h("span", { class: "text-xs" }, value === null || value === undefined ? "" : String(value))
		}
	}))

	columns.push({
		title: "",
		key: "_chevron",
		width: 36,
		align: "center",
		render: () => h(Icon, { name: "carbon:chevron-right", size: 14, class: "text-secondary" })
	})

	return columns
})

function rowProps(row: Record<string, unknown>) {
	return {
		style: "cursor: pointer",
		onClick: () => emit("inspect", row)
	}
}
</script>
