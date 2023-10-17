<template>
	<apexchart
		:width="width"
		:height="height"
		v-if="ready"
		:type="type"
		:options="options"
		:series="series"
		ref="chart"
	></apexchart>
</template>

<script lang="ts" setup>
import { useThemeStore } from "@/stores/theme"
import { toRefs, ref, onMounted, nextTick } from "vue"

export interface VueApexChartsComponent {
	type?:
		| "line"
		| "area"
		| "bar"
		| "histogram"
		| "pie"
		| "donut"
		| "radialBar"
		| "rangeBar"
		| "scatter"
		| "bubble"
		| "heatmap"
		| "candlestick"
		| "radar"
		| "polarArea"
	updateSeries(newSeries: any, animate?: boolean): Promise<void>
	refresh(): Promise<void>
}

const props = defineProps<{
	width?: string | number
	height?: string | number
	type?: VueApexChartsComponent["type"]
	options?: any
	series?: any
}>()
const { width, height, type, options, series } = toRefs(props)

const emit = defineEmits<{
	(e: "mounted", value: VueApexChartsComponent): void
}>()

const ready = ref(false)
const chart = ref<VueApexChartsComponent | null>()
const store = useThemeStore()

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
