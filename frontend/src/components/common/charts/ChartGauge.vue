<template>
	<VChart class="w-full" autoresize :option="chartOption" :style="{ height: `${height}px` }" />
</template>

<script setup lang="ts">
import type { GaugeSeriesOption } from "echarts/charts"
import type { GridComponentOption, TooltipComponentOption } from "echarts/components"
import type { ComposeOption } from "echarts/core"
import type { CardLinkColor } from "@/components/common/cards/CardLink.vue"
import { GaugeChart } from "echarts/charts"
import { GridComponent, TooltipComponent } from "echarts/components"
import { use } from "echarts/core"
import { CanvasRenderer } from "echarts/renderers"
import { computed, toRefs } from "vue"
import VChart from "vue-echarts"
import { useThemeStore } from "@/stores/theme"

const props = withDefaults(
	defineProps<{
		value: number
		title?: string
		height?: number
		/** Valori alti = stato sano (es. CPU idle). Valori bassi = sano se false (es. CPU usage). */
		highIsGood?: boolean
		/** Forza un colore semantico al posto delle soglie automatiche. */
		color?: CardLinkColor
	}>(),
	{
		title: "",
		height: 220,
		highIsGood: true
	}
)

use([CanvasRenderer, GaugeChart, TooltipComponent, GridComponent])

type ChartOption = ComposeOption<TooltipComponentOption | GridComponentOption | GaugeSeriesOption>

const GAUGE_POINTER_ICON = "path://M12.8,0.7l12,40.1H0.7L12.8,0.7z"

const { value, title, height, highIsGood, color } = toRefs(props)
const style = computed(() => useThemeStore().style)

const percentValue = computed(() => Math.min(100, Math.max(0, Math.round(value.value * 10) / 10)))
const gaugeRatio = computed(() => percentValue.value / 100)

function resolveAccentColor(percent: number, theme: Record<string, string>): string {
	if (color.value === "danger") return theme["error-color"]
	if (color.value === "warning") return theme["warning-color"]
	if (color.value === "success") return theme["success-color"]
	if (color.value === "primary") return theme["primary-color"]

	const healthy = highIsGood.value ? percent >= 50 : percent <= 50
	const caution = highIsGood.value ? percent >= 20 : percent <= 80

	if (healthy) return theme["success-color"]
	if (caution) return theme["warning-color"]
	return theme["error-color"]
}

function buildAxisGradient(theme: Record<string, string>): [number, string][] {
	const error = theme["error-color"]
	const warning = theme["warning-color"]
	const success = theme["success-color"]

	if (highIsGood.value) {
		return [
			[0.2, error],
			[0.5, warning],
			[1, success]
		]
	}

	return [
		[0.5, success],
		[0.8, warning],
		[1, error]
	]
}

const chartOption = computed((): ChartOption => {
	const theme = style.value
	const fgDefault = theme["fg-default-color"]
	const fgSecondary = theme["fg-secondary-color"]
	const fgTertiary = theme["fg-tertiary-color"]
	const fontMono = theme["font-family-mono"]
	const accentColor = resolveAccentColor(percentValue.value, theme)
	const ratio = gaugeRatio.value

	return {
		backgroundColor: "transparent",
		series: [
			{
				type: "gauge",
				startAngle: 205,
				endAngle: -25,
				center: ["50%", "72%"],
				radius: "92%",
				min: 0,
				max: 1,
				splitNumber: 8,
				pointer: {
					icon: GAUGE_POINTER_ICON,
					length: "14%",
					width: 14,
					offsetCenter: [0, "-56%"],
					itemStyle: { color: fgDefault }
				},
				axisLine: {
					roundCap: true,
					lineStyle: {
						width: 6,
						color: buildAxisGradient(theme)
					}
				},
				axisTick: {
					length: 8,
					lineStyle: { color: fgTertiary, width: 1 }
				},
				splitLine: {
					length: 14,
					lineStyle: { color: fgSecondary, width: 2 }
				},
				axisLabel: {
					show: true,
					distance: -46,
					color: fgSecondary,
					fontSize: 10,
					fontFamily: fontMono,
					formatter: (axisValue: number) => {
						if (axisValue === 0) return "0%"
						if (axisValue === 0.5) return "50%"
						if (axisValue === 1) return "100%"
						return ""
					}
				},
				title: title.value
					? {
							show: true,
							offsetCenter: [0, "18%"],
							color: fgSecondary,
							fontSize: 11,
							fontWeight: 500,
							fontFamily: theme["font-family"]
						}
					: { show: false },
				detail: {
					show: true,
					offsetCenter: [0, "-22%"],
					valueAnimation: true,
					color: accentColor,
					formatter: () => `{value|${Math.round(ratio * 100)}}{unit|%}`,
					rich: {
						value: {
							color: fgDefault,
							fontSize: 32,
							fontWeight: 600,
							fontFamily: fontMono,
							lineHeight: 36
						},
						unit: {
							color: fgSecondary,
							fontSize: 14,
							fontWeight: 500,
							fontFamily: fontMono,
							padding: [4, 0, 0, 2]
						}
					}
				},
				data: [{ value: ratio, name: title.value }]
			}
		]
	}
})
</script>
