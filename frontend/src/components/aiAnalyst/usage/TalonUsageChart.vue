<template>
	<VChart
		v-if="option"
		class="w-full"
		autoresize
		:option
		:style="{ height: `${height}px`, width: '100%' }"
		role="img"
		:aria-label="usageChartSummary(report)"
		data-testid="talon-usage-chart"
	/>
</template>

<script setup lang="ts">
// Cost per group (the option and its design notes: ./usage-chart.ts). Drawn from parsed amounts;
// every figure a reader sees (the tooltip, the table) is the API's string.
import type { TalonUsageReport } from "@/types/talonUsage"
import { BarChart } from "echarts/charts"
import { GridComponent, TooltipComponent } from "echarts/components"
import { use } from "echarts/core"
import { CanvasRenderer } from "echarts/renderers"
import { computed } from "vue"
import VChart from "vue-echarts"
import { useThemeStore } from "@/stores/theme"
import { buildUsageChartOption, usageChartBars, usageChartSummary } from "./usage-chart"

const { report } = defineProps<{ report: TalonUsageReport }>()

use([CanvasRenderer, BarChart, GridComponent, TooltipComponent])

const theme = useThemeStore()
const option = computed(() => buildUsageChartOption(report, theme.style, theme.isThemeDark))
const height = computed(() =>
	report.group_by === "day" ? 240 : Math.max(120, usageChartBars(report).length * 30 + 40)
)
</script>
