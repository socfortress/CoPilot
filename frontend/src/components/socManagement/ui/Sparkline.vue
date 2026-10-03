<template>
	<VChart
		v-if="values.length > 1"
		class="sparkline shrink-0"
		:option
		:init-options="{ renderer: 'svg' }"
		:style="{ width: `${width}px`, height: `${height}px` }"
		role="img"
		:aria-label="`Trend over ${values.length} periods, peak ${peak}`"
	/>
</template>

<script setup lang="ts">
// A one-series trend in the row it belongs to: no axes, no tooltip, the last value
// marked. SVG renderer: a table can hold a few dozen of these, and a canvas each would
// cost far more than the line it draws.
import type { LineSeriesOption } from "echarts/charts"
import type { GridComponentOption } from "echarts/components"
import type { ComposeOption } from "echarts/core"
import { LineChart } from "echarts/charts"
import { GridComponent } from "echarts/components"
import { use } from "echarts/core"
import { SVGRenderer } from "echarts/renderers"
import { computed } from "vue"
import VChart from "vue-echarts"
import { useThemeStore } from "@/stores/theme"
import { useSocChartColors } from "../charts/chart-colors"

const { values, width = 88, height = 24 } = defineProps<{ values: number[]; width?: number; height?: number }>()

use([SVGRenderer, LineChart, GridComponent])

const theme = useThemeStore()
const { primary } = useSocChartColors()

const peak = computed(() => Math.max(0, ...values))

const option = computed((): ComposeOption<LineSeriesOption | GridComponentOption> => {
	const color = primary.value
	const lastIndex = values.length - 1
	return {
		backgroundColor: "transparent",
		animation: false,
		grid: { left: 3, right: 3, top: 3, bottom: 3 },
		xAxis: { type: "category", show: false, boundaryGap: false, data: values.map((_, i) => i) },
		yAxis: { type: "value", show: false, min: 0, max: Math.max(1, peak.value) },
		series: [
			{
				type: "line",
				silent: true,
				symbol: "none",
				showSymbol: true,
				lineStyle: { width: 1.5, color, cap: "round", join: "round" },
				areaStyle: { color, opacity: 0.12 },
				data: values.map((value, i) =>
					i === lastIndex
						? {
								value,
								symbol: "circle",
								symbolSize: 5,
								itemStyle: { color, borderColor: theme.style["bg-default-color"], borderWidth: 1.5 }
							}
						: value
				)
			}
		]
	}
})
</script>
