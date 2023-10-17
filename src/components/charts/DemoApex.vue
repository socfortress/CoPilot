<template>
	<apexchart
		ref="chart"
		width="100%"
		height="100%"
		v-if="ready"
		:type="type"
		:options="options"
		:series="series"
		:class="{ 'time-buttons': timeButtons }"
		:style="legendOffset && `--legend-offset:${legendOffset}px`"
	></apexchart>
</template>

<script lang="ts" setup>
import { useThemeStore } from "@/stores/theme"
import { computed, onMounted, toRefs, watch, watchEffect, nextTick } from "vue"
import { ref } from "vue"
import { getAreaOpts, getBarOpts, getMonthsSeries, getWeekSeries, getYearsSeries } from "./data"
import { getChartColors, getHighlightMap } from "./utils"

export interface VueApexChartsComponent {
	toggleSeries(seriesName: string): any
	options: {
		colors?: string[]
	}
	series?: any[]
}

export type DataType = "years" | `years-${number}` | "months" | "week"
export type ChartsType = "area" | "bar"

export type ChartCTX = VueApexChartsComponent

const emit = defineEmits<{
	(e: "mounted", value: VueApexChartsComponent): void
}>()

const props = withDefaults(
	defineProps<{
		type: ChartsType
		dataType?: DataType
		dark?: boolean
		highlight?: boolean
		colorsRandom?: boolean
		colorsSecondary?: boolean
		color?: string
		fontColor?: string
		strokeWidth?: number
		legendOffset?: number
		seriesList?: string[]
		timeButtons?: boolean
		hideLegend?: boolean
		hideXaxisLabels?: boolean
	}>(),
	{
		dark: undefined,
		dataType: "years",
		highlight: false,
		colorsRandom: false,
		colorsSecondary: false,
		timeButtons: false,
		hideLegend: false,
		hideXaxisLabels: false,
		seriesList: () => ["Trend"]
	}
)
const {
	type,
	dark,
	dataType,
	highlight,
	colorsRandom,
	colorsSecondary,
	color,
	fontColor,
	strokeWidth,
	seriesList,
	timeButtons,
	legendOffset,
	hideLegend,
	hideXaxisLabels
} = toRefs(props)

const ready = ref(false)
const chart = ref<VueApexChartsComponent | null>()

const isThemeDark = computed(() => useThemeStore().isThemeDark)
const style: { [key: string]: any } = computed(() => useThemeStore().style)

const customButtons = [
	{
		icon: "years",
		title: "years view",
		class: "custom-icon",
		click: function () {
			setData("years")
		}
	},
	{
		icon: "months",
		title: "months view",
		class: "custom-icon",
		click: function () {
			setData("months")
		}
	},
	{
		icon: "week",
		title: "week view",
		class: "custom-icon",
		click: function () {
			setData("week")
		}
	}
]

const series = ref<any[]>([])
const categories = ref<any[]>([])

function setData(type: DataType) {
	series.value = []
	categories.value = []

	if (type === "years") {
		for (const name of seriesList.value) {
			const data = getYearsSeries({ name })
			series.value.push(data.series)
			if (!categories.value.length) {
				categories.value = data.categories
			}
		}
	}
	if (type.startsWith("years-")) {
		const years = type.split("-")[1]
		for (const name of seriesList.value) {
			const data = getYearsSeries({ yearsCount: +years, name })
			series.value.push(data.series)
			if (!categories.value.length) {
				categories.value = data.categories
			}
		}
	}
	if (type === "months") {
		for (const name of seriesList.value) {
			const data = getMonthsSeries({ name })
			series.value.push(data.series)
			if (!categories.value.length) {
				categories.value = data.categories
			}
		}
	}
	if (type === "week") {
		for (const name of seriesList.value) {
			const data = getWeekSeries({ name })
			series.value.push(data.series)
			if (!categories.value.length) {
				categories.value = data.categories
			}
		}
	}
}

setData(dataType.value)

const highlightMap = getHighlightMap(series.value[0].data)

const secondaryColors = computed(() => Object.values(useThemeStore().secondaryColors))
const palette = computed<string[]>(() => new Array(4).fill(secondaryColors.value).flat())

const optsFunction = type.value === "area" ? getAreaOpts : getBarOpts
const getArgs = () => ({
	dark: dark.value === undefined ? isThemeDark.value : dark.value,
	colors: colorsSecondary.value
		? palette.value
		: getChartColors({
				type: colorsRandom.value ? "random" : undefined,
				color: color?.value ?? style.value["--primary-color"],
				highlight: highlight.value ? highlightMap : undefined
		  }) /*eslint no-mixed-spaces-and-tabs: "off"*/,
	fontColor:
		fontColor?.value || colorsRandom.value || color?.value
			? style.value["--fg-secondary-color"]
			: style.value["--primary-color"],
	fontFamily: style.value["--font-family-mono"],
	categories: categories.value,
	strokeWidth: strokeWidth?.value,
	hideLegend: hideLegend?.value,
	hideXaxisLabels: hideXaxisLabels?.value,
	customButtons: timeButtons.value ? customButtons : []
})

const store = useThemeStore()
const options = ref(optsFunction(getArgs()))

watch(dataType, () => {
	setData(dataType.value)
})

watchEffect(async () => {
	options.value = optsFunction(getArgs())
})

onMounted(() =>
	nextTick(() => {
		const duration = 1000 * store.routerTransitionDuration
		const gap = 500

		// TIMEOUT REQUIRED BY PAGE ANIMATION
		setTimeout(() => {
			ready.value = true

			setTimeout(() => {
				if (chart.value) {
					emit("mounted", chart.value)
				}
			}, 100)
		}, duration + gap)
	})
)
</script>

<style scoped lang="scss">
.vue-apexcharts {
	height: 100%;

	:deep() {
		.apexcharts-canvas {
			height: 100% !important;

			.apexcharts-legend {
				top: 28px !important;
				right: var(--legend-offset, 0) !important;
				padding: 0;
				.apexcharts-legend-series {
					display: inline-block;
					.apexcharts-legend-marker {
						z-index: 1;
						margin-right: -6px;
						margin-left: 4px;
					}
					.apexcharts-legend-text {
						background-color: var(--tab-color-active);
						padding: 0px 12px;
						padding-left: 24px;
						border-radius: var(--border-radius);
						border: 1px solid var(--border-color);
						box-sizing: border-box;
						height: 34px;
						font-size: 14px !important;
						font-family: var(--font-family) !important;
						display: inline-block;
						color: var(--fg-color) !important;
						line-height: 34px;
					}
				}
			}
		}
	}
	&.time-buttons {
		:deep() {
			.apexcharts-legend {
				right: 239px !important;
			}
			.apexcharts-toolbar {
				max-width: 100%;
				z-index: 0;
				top: 30px !important;
				right: 25px !important;
				display: flex;
				gap: 4px;
				.apexcharts-toolbar-custom-icon {
					background-color: var(--tab-color-active);
					padding: 0px 8px;
					border-radius: var(--border-radius);
					border: 1px solid var(--border-color);
					box-sizing: border-box;
					height: 34px;
					font-size: 14px !important;
					font-family: var(--font-family) !important;
					display: inline-block;
					line-height: 34px;
					width: 70px;
					text-transform: capitalize;
					color: var(--fg-color);
				}
			}
		}
	}
}
</style>
