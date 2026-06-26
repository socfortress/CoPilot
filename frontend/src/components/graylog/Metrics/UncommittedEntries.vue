<template>
	<div class="flex w-full flex-col gap-3">
		<div class="border-default bg-default flex rounded-lg border">
			<div class="grow">
				<div class="flex grow items-center gap-3 px-5.5 py-4.5 text-lg font-bold">
					<Icon v-if="isWarning" :name="DangerIcon" class="text-warning" />
					<span>Uncommitted Journal Entries</span>
				</div>
				<VChart class="h-17.5 w-full" autoresize :option="chartOption" />
			</div>
			<div
				class="flex min-w-20 flex-col justify-center rounded-r-lg px-5.5 py-4.5 text-center font-mono text-xl"
				:class="isWarning ? 'bg-warning/5 text-warning' : 'bg-secondary'"
			>
				<span>{{ value }}</span>
			</div>
		</div>
		<div class="footer">
			<n-button
				type="primary"
				ghost
				icon-placement="right"
				@click="routeGraylogManagement('messages').navigate()"
			>
				<template #icon>
					<Icon :name="LinkIcon" :size="14" />
				</template>
				See messages
			</n-button>
		</div>
	</div>
</template>

<script setup lang="ts">
import type { LineSeriesOption } from "echarts/charts"
import type { GridComponentOption, TooltipComponentOption } from "echarts/components"
import type { ComposeOption } from "echarts/core"
import { LineChart } from "echarts/charts"
import { GridComponent, TooltipComponent } from "echarts/components"
import { use } from "echarts/core"
import { CanvasRenderer } from "echarts/renderers"
import { NButton } from "naive-ui"
import { computed, ref, toRefs, watch } from "vue"
import VChart from "vue-echarts"
import {
	buildChartTooltipGlassBase,
	chartTooltipThemeFromStyle,
	formatChartTooltipTimeAxisFirst
} from "@/components/common/charts"
import Icon from "@/components/common/Icon.vue"
import { useNavigation } from "@/composables/useNavigation"
import { useHealthcheckStore } from "@/stores/healthcheck"
import { useThemeStore } from "@/stores/theme"
import dayjs from "@/utils/dayjs"

const props = defineProps<{
	value: number
}>()

use([CanvasRenderer, LineChart, TooltipComponent, GridComponent])

type ChartOption = ComposeOption<TooltipComponentOption | GridComponentOption | LineSeriesOption>

const MAX_POINTS = 100
const CHART_ANIMATION_MAX_POINTS = 100

const UNCOMMITTED_JOURNAL_ENTRIES_THRESHOLD = useHealthcheckStore().uncommittedJournalEntriesThreshold

const { value } = toRefs(props)

const LinkIcon = "carbon:launch"
const DangerIcon = "majesticons:exclamation-line"

const style = computed(() => useThemeStore().style)
const { routeGraylogManagement } = useNavigation()

const dataPoints = ref<[number, number][]>([])

const isWarning = computed<boolean>(() => value.value > UNCOMMITTED_JOURNAL_ENTRIES_THRESHOLD)

const enableAnimation = computed(() => dataPoints.value.length < CHART_ANIMATION_MAX_POINTS)

const chartOption = computed((): ChartOption => {
	const primary = style.value["primary-color"]

	return {
		backgroundColor: "transparent",
		grid: { left: 0, right: 0, top: 2, bottom: 2 },
		xAxis: {
			type: "time",
			show: false
		},
		yAxis: {
			type: "value",
			show: false,
			scale: true
		},
		tooltip: {
			...buildChartTooltipGlassBase(
				chartTooltipThemeFromStyle({
					...style.value,
					"font-family": style.value["font-family-mono"]
				}),
				{ trigger: "axis" }
			),
			formatter: params =>
				formatChartTooltipTimeAxisFirst(params, {
					formatTime: ts => dayjs(ts).format("HH:mm:ss"),
					resolveColor: () => primary
				})
		},
		series: [
			{
				name: "Entries",
				type: "line",
				showSymbol: false,
				smooth: false,
				lineStyle: { width: 3, color: primary },
				areaStyle: { color: primary, opacity: 0.12 },
				animation: enableAnimation.value,
				animationDurationUpdate: 200,
				data: dataPoints.value
			}
		]
	}
})

watch(value, val => {
	if (dataPoints.value.length >= MAX_POINTS) {
		dataPoints.value.shift()
	}
	dataPoints.value.push([Date.now(), val])
})
</script>
