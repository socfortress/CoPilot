<template>
	<VChart
		ref="chart"
		class="w-full"
		autoresize
		:option
		:style="{ height: `${height}px`, width: '100%' }"
		role="img"
		:aria-label="summary"
		data-testid="cloud-trend-chart"
		@zr:click="onClick"
	/>
</template>

<script setup lang="ts">
// The columns of the failures-over-time section (trend.ts builds the option). A click anywhere in
// a column's slot, not only on its painted segments, opens that scan.
import type { TrendPoint } from "./trend"
import { BarChart } from "echarts/charts"
import { GridComponent, TooltipComponent } from "echarts/components"
import { use } from "echarts/core"
import { CanvasRenderer } from "echarts/renderers"
import { computed, useTemplateRef } from "vue"
import VChart from "vue-echarts"
import { useSettingsStore } from "@/stores/settings"
import { useThemeStore } from "@/stores/theme"
import dayjs from "@/utils/dayjs"
import { formatDate } from "@/utils/format"
import { buildTrendOption, trendSummary } from "./trend"

const {
	points,
	selectedId,
	height = 200
} = defineProps<{
	points: TrendPoint[]
	selectedId: number | null
	height?: number
}>()

const emit = defineEmits<{ (e: "select", scanId: number): void }>()

use([CanvasRenderer, BarChart, GridComponent, TooltipComponent])

const theme = useThemeStore()
const dFormats = useSettingsStore().dateFormat
const chart = useTemplateRef<InstanceType<typeof VChart>>("chart")

function label(at: string): string {
	return at ? dayjs(at).format("D MMM") : ""
}

function when(at: string): string {
	return at ? String(formatDate(at, dFormats.datetime)) : ""
}

const option = computed(() =>
	buildTrendOption(points, { style: theme.style, dark: theme.isThemeDark, selectedId, label, when })
)
const summary = computed(() => trendSummary(points, at => String(formatDate(at, dFormats.date))))

function onClick(event: { offsetX: number; offsetY: number }) {
	const instance = chart.value
	const pixel = [event.offsetX, event.offsetY]
	if (!instance?.containPixel({ gridIndex: 0 }, pixel)) return
	const [index] = instance.convertFromPixel({ gridIndex: 0 }, pixel) as number[]
	const point = points[Math.round(index ?? -1)]
	if (point) emit("select", point.id)
}
</script>
