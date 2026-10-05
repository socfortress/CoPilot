<template>
	<VChart
		v-if="hasData"
		class="w-full"
		autoresize
		:option
		:style="{ height: `${height}px`, width: '100%' }"
		role="img"
		:aria-label="`Resolution SLA met per ${bucket}, objective ${objective}%`"
	/>
	<n-empty
		v-else
		description="No SLA outcome in this period yet"
		class="justify-center"
		:style="{ height: `${height}px` }"
	/>
</template>

<script setup lang="ts">
// Resolution SLA met, by opening bucket: one series (so no legend — the panel title
// names it), the objective as a reference line. A bucket with no outcome is a gap,
// never a drop to 0%.
import type { LineSeriesOption } from "echarts/charts"
import type { GridComponentOption, MarkLineComponentOption, TooltipComponentOption } from "echarts/components"
import type { ComposeOption } from "echarts/core"
import type { SocBucket, TrendPoint } from "@/types/soc-management"
import { LineChart } from "echarts/charts"
import { GridComponent, MarkLineComponent, TooltipComponent } from "echarts/components"
import { use } from "echarts/core"
import { CanvasRenderer } from "echarts/renderers"
import { NEmpty } from "naive-ui"
import { computed } from "vue"
import VChart from "vue-echarts"
import { buildChartTooltipGlassBase, chartTooltipThemeFromStyle } from "@/components/common/charts"
import { useThemeStore } from "@/stores/theme"
import { formatBucket, RATE_GOOD } from "../utils"
import { useSocChartColors } from "./chart-colors"

const {
	points,
	bucket,
	objective = RATE_GOOD,
	height = 220
} = defineProps<{ points: TrendPoint[]; bucket: SocBucket; objective?: number; height?: number }>()

use([CanvasRenderer, LineChart, GridComponent, TooltipComponent, MarkLineComponent])

const theme = useThemeStore()
const { primary } = useSocChartColors()

const hasData = computed(() => points.some(p => p.sla_rate != null))

const option = computed(
	(): ComposeOption<LineSeriesOption | GridComponentOption | TooltipComponentOption | MarkLineComponentOption> => {
		const style = theme.style
		const muted = style["fg-secondary-color"]
		const hairline = style["border-color"]
		const font = style["font-family"]
		const labels = points.map(p => formatBucket(p.start, bucket))
		const color = primary.value

		return {
			backgroundColor: "transparent",
			grid: { left: 8, right: 40, top: 12, bottom: 4, outerBoundsMode: "same", outerBoundsContain: "axisLabel" },
			tooltip: {
				...buildChartTooltipGlassBase(chartTooltipThemeFromStyle(style), { trigger: "axis" }),
				axisPointer: { type: "line", lineStyle: { color: muted, width: 1 } },
				formatter: params => {
					const row = Array.isArray(params) ? params[0] : params
					const value = row?.value as number | null | undefined
					return `<div style="padding:8px 10px"><div style="color:${muted};font-size:11px">${labels[row?.dataIndex ?? 0] ?? ""}</div>
						<div style="margin-top:2px">${value == null ? "no outcome yet" : `<b style="font-variant-numeric:tabular-nums">${value.toFixed(1)}%</b> resolved in SLA`}</div></div>`
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
				min: 0,
				max: 100,
				interval: 25,
				axisLabel: { color: muted, fontFamily: font, fontSize: 11, formatter: "{value}%" },
				splitLine: { lineStyle: { color: hairline, width: 1, type: "solid" } }
			},
			series: [
				{
					type: "line",
					name: "Resolved in SLA",
					data: points.map(p => p.sla_rate),
					connectNulls: false,
					smooth: false,
					symbol: "circle",
					symbolSize: 8,
					showSymbol: points.filter(p => p.sla_rate != null).length < 2,
					lineStyle: { width: 2, color, cap: "round", join: "round" },
					itemStyle: { color, borderColor: style["bg-default-color"], borderWidth: 2 },
					areaStyle: { color, opacity: 0.1 },
					emphasis: { focus: "none", scale: false },
					markLine: {
						silent: true,
						symbol: "none",
						lineStyle: { color: muted, width: 1, type: [4, 3] },
						label: {
							formatter: `${objective}%`,
							color: muted,
							fontFamily: font,
							fontSize: 11,
							position: "end"
						},
						data: [{ yAxis: objective }]
					}
				}
			]
		}
	}
)
</script>
