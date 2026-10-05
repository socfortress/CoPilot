<template>
	<div class="flex flex-col gap-2">
		<div class="flex flex-wrap items-center gap-4 text-xs" role="list" aria-label="Legend">
			<span
				v-for="item of legend"
				:key="item.name"
				class="text-secondary inline-flex items-center gap-1.5"
				role="listitem"
			>
				<span class="inline-block h-0.5 w-4 rounded-full" :style="{ backgroundColor: item.color }" />
				{{ item.name }}
				<b class="text-default font-mono">{{ item.total.toLocaleString() }}</b>
			</span>
		</div>
		<VChart
			v-if="hasData"
			class="w-full"
			autoresize
			:option
			:style="{ height: `${height}px`, width: '100%' }"
			role="img"
			:aria-label
		/>
		<n-empty
			v-else
			:description="`No ${noun}s in this period`"
			class="justify-center"
			:style="{ height: `${height}px` }"
		/>
	</div>
</template>

<script setup lang="ts">
// Opened vs resolved per bucket — two series on one axis (same unit), a legend that
// also carries the totals, a crosshair tooltip. 2px lines, a 10% wash under the lead
// series only, hairline solid grid.
import type { LineSeriesOption } from "echarts/charts"
import type { GridComponentOption, TooltipComponentOption } from "echarts/components"
import type { ComposeOption } from "echarts/core"
import type { SocBucket, TrendPoint } from "@/types/soc-management"
import { LineChart } from "echarts/charts"
import { GridComponent, TooltipComponent } from "echarts/components"
import { use } from "echarts/core"
import { CanvasRenderer } from "echarts/renderers"
import { NEmpty } from "naive-ui"
import { computed } from "vue"
import VChart from "vue-echarts"
import { buildChartTooltipGlassBase, chartTooltipThemeFromStyle } from "@/components/common/charts"
import { useThemeStore } from "@/stores/theme"
import { formatBucket } from "../utils"
import { useSocChartColors } from "./chart-colors"

const {
	points,
	bucket,
	entity = "alert",
	height = 240
} = defineProps<{
	points: TrendPoint[]
	bucket: SocBucket
	entity?: "alert" | "case"
	height?: number
}>()

use([CanvasRenderer, LineChart, GridComponent, TooltipComponent])

const theme = useThemeStore()
const { primary, secondary } = useSocChartColors()

const noun = computed(() => entity)
const opened = computed(() => points.map(p => (entity === "alert" ? p.alerts_opened : p.cases_opened)))
const resolved = computed(() => points.map(p => (entity === "alert" ? p.alerts_resolved : p.cases_resolved)))
const sum = (values: number[]) => values.reduce((total, value) => total + value, 0)
const hasData = computed(() => sum(opened.value) + sum(resolved.value) > 0)

const legend = computed(() => [
	{ name: "Opened", color: primary.value, total: sum(opened.value) },
	{ name: "Resolved", color: secondary.value, total: sum(resolved.value) }
])

const ariaLabel = computed(
	() =>
		`${noun.value}s opened and resolved per ${bucket}: ${sum(opened.value)} opened, ${sum(resolved.value)} resolved`
)

const option = computed((): ComposeOption<LineSeriesOption | GridComponentOption | TooltipComponentOption> => {
	const style = theme.style
	const muted = style["fg-secondary-color"]
	const hairline = style["border-color"]
	const font = style["font-family"]
	const labels = points.map(p => formatBucket(p.start, bucket))

	const series = (name: string, data: number[], color: string, wash: boolean): LineSeriesOption => ({
		type: "line",
		name,
		data,
		smooth: false,
		symbol: "circle",
		symbolSize: 8,
		showSymbol: false,
		lineStyle: { width: 2, color, cap: "round", join: "round" },
		itemStyle: { color, borderColor: style["bg-default-color"], borderWidth: 2 },
		areaStyle: wash ? { color, opacity: 0.1 } : undefined,
		emphasis: { focus: "none", scale: false }
	})

	return {
		backgroundColor: "transparent",
		grid: { left: 8, right: 16, top: 12, bottom: 4, outerBoundsMode: "same", outerBoundsContain: "axisLabel" },
		tooltip: {
			...buildChartTooltipGlassBase(chartTooltipThemeFromStyle(style), { trigger: "axis" }),
			axisPointer: { type: "line", lineStyle: { color: muted, width: 1 } },
			formatter: params => {
				const rows = Array.isArray(params) ? params : [params]
				const index = rows[0]?.dataIndex ?? 0
				const lines = rows
					.map(
						row =>
							`<div style="display:flex;align-items:center;gap:6px;margin-top:2px">
								<span style="display:inline-block;width:8px;height:8px;border-radius:50%;background:${row.color}"></span>
								${row.seriesName}<b style="margin-left:auto;padding-left:12px;font-variant-numeric:tabular-nums">${Number(row.value).toLocaleString()}</b>
							</div>`
					)
					.join("")
				return `<div style="padding:8px 10px"><div style="color:${muted};font-size:11px">${labels[index] ?? ""}</div>${lines}</div>`
			}
		},
		xAxis: {
			type: "category",
			boundaryGap: false,
			data: labels,
			axisLine: { lineStyle: { color: hairline } },
			axisTick: { show: false },
			axisLabel: { color: muted, fontFamily: font, fontSize: 11, hideOverlap: true }
		},
		yAxis: {
			type: "value",
			minInterval: 1,
			splitNumber: 3,
			axisLabel: { color: muted, fontFamily: font, fontSize: 11, formatter: (v: number) => v.toLocaleString() },
			splitLine: { lineStyle: { color: hairline, width: 1, type: "solid" } }
		},
		series: [
			series("Opened", opened.value, primary.value, true),
			series("Resolved", resolved.value, secondary.value, false)
		]
	}
})
</script>
