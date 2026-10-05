<template>
	<VChart
		v-if="history.points.length"
		class="w-full"
		autoresize
		:option
		:style="{ height: `${height}px`, width: '100%' }"
		role="img"
		:aria-label="riskChartSummary(history)"
	/>
</template>

<script setup lang="ts">
// An entity's UBA risk over time (the option and its design notes: ./risk-chart.ts).
import type { UbaRiskHistory } from "@/types/uba"
import { LineChart, ScatterChart } from "echarts/charts"
import { GridComponent, LegendComponent, MarkLineComponent, TooltipComponent } from "echarts/components"
import { use } from "echarts/core"
import { CanvasRenderer } from "echarts/renderers"
import { computed } from "vue"
import VChart from "vue-echarts"
import { useThemeStore } from "@/stores/theme"
import { buildRiskChartOption, riskChartSummary } from "./risk-chart"

const { history, height = 200 } = defineProps<{ history: UbaRiskHistory; height?: number }>()

use([CanvasRenderer, LineChart, ScatterChart, GridComponent, LegendComponent, MarkLineComponent, TooltipComponent])

const theme = useThemeStore()
const option = computed(() => buildRiskChartOption(history, theme.style, theme.isThemeDark))
</script>
