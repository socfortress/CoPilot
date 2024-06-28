<template>
	<n-card class="top-indices-chart-container" title="Top 8 indices size & health" segmented>
		<n-spin style="height: 400px; overflow: hidden" :show="loading">
			<div class="overflow-hidden">
				<div id="top-indices-chart" style="max-width: 100%; height: 400px"></div>
			</div>
		</n-spin>
	</n-card>
</template>

<script setup lang="ts">
import { type ECharts, init as echartsInit, use as echartsUse } from "echarts/core"
import { CanvasRenderer } from "echarts/renderers"
import { PieChart } from "echarts/charts"
import { TooltipComponent, LegendComponent, GridComponent } from "echarts/components"

import { computed, onMounted, ref, toRefs, watch } from "vue"
import { type IndexStats, IndexHealth } from "@/types/indices.d"
import bytes from "bytes"
import _ from "lodash"
import { NSpin, NCard } from "naive-ui"
import { useThemeStore } from "@/stores/theme"

const props = defineProps<{
	indices: IndexStats[] | null
}>()
const { indices } = toRefs(props)

const style = computed(() => useThemeStore().style)
const loading = computed(() => !indices?.value || indices.value === null)
const chartCtx = ref<ECharts | null>(null)

function getOptions() {
	const data = _.chain(indices.value || [])
		.map(i => {
			if (typeof i.store_size === "string") {
				i.store_size_value = bytes(i.store_size)
			} else {
				i.store_size_value = i.store_size
			}
			return i
		})
		.orderBy(["store_size"], ["desc"])
		.slice(0, 8)
		.value()

	const green = (indices.value || []).filter(i => i.health === IndexHealth.GREEN).length
	const yellow = (indices.value || []).filter(i => i.health === IndexHealth.YELLOW).length
	const red = (indices.value || []).filter(i => i.health === IndexHealth.RED).length

	const sizeData: { value: number; name: string }[] = data.map(i => ({
		value: i.store_size_value || 0,
		name: i.index
	}))

	return {
		tooltip: {
			trigger: "item",
			formatter: "{a}<hr/>{b}: <strong>{c}</strong> ({d}%)"
		},
		legend: {
			data: sizeData.map(i => i.name),
			left: "left",
			type: "scroll",
			textStyle: {
				color: style.value["fg-color"]
			},
			pageTextStyle: {
				color: style.value["fg-color"]
			}
		},
		grid: {
			top: "0%",
			bottom: "0%",
			height: "80%"
		},
		series: [
			{
				name: "Indices Health",
				top: "-35%",
				bottom: "-50%",
				zlevel: 1,
				type: "pie",
				radius: [0, "20%"],
				label: {
					show: false
				},
				itemStyle: {
					borderColor: style.value["bg-color"],
					borderWidth: 2
				},
				data: [
					{ value: green, name: "Green", itemStyle: { color: style.value["success-color"] } },
					{ value: yellow, name: "Yellow", itemStyle: { color: style.value["warning-color"] } },
					{ value: red, name: "Red", itemStyle: { color: style.value["error-color"] } }
				]
			},
			{
				name: "Indices Size",
				type: "pie",
				top: "-35%",
				bottom: "-50%",
				color: [
					"#082f49",
					"#0c4a6e",
					"#075985",
					"#0369a1",
					"#0284c7",
					"#0ea5e9",
					"#38bdf8",
					"#7dd3fc",
					"#bae6fd"
				],
				tooltip: {
					formatter: (params: { seriesName: string; name: string; value: number; percent: number }) => {
						return `${params.seriesName}<hr/>${params.name}<br/><strong>${bytes(params.value)}</strong>  (${
							params.percent
						}%)`
					}
				},
				avoidLabelOverlap: true,
				radius: ["24%", "35%"],
				minAngle: 5,
				zlevel: 2,
				labelLine: {
					length: 25,
					length2: 5,
					showAbove: true,
					lineStyle: {
						width: 1.5,
						type: "dashed"
					}
				},
				label: {
					formatter: "{name|{b}}\n{per|{d}%}",
					minMargin: 10,
					edgeDistance: 10,
					lineHeight: 15,
					//alignTo: "edge",
					rich: {
						name: {
							color: style.value["fg-color"],
							fontSize: window.innerWidth > 1000 ? 13 : 11
						},
						per: {
							fontSize: window.innerWidth > 1000 ? 13 : 11,
							fontWeight: "bold",
							color: style.value["fg-color"]
						}
					}
				},
				labelLayout: function (params: {
					labelLinePoints: Array<number[]>
					labelRect: { x: number; width: number }
				}) {
					const isLeft = chartCtx.value ? params.labelRect.x < chartCtx.value.getWidth() / 2 : false
					const points = params.labelLinePoints
					// Update the end point.
					points[2][0] = isLeft ? params.labelRect.x : params.labelRect.x + params.labelRect.width
					return {
						labelLinePoints: points,
						hideOverlap: false,
						moverOverlap: "shiftX",
						draggable: true
					}
				},
				itemStyle: {
					borderColor: style.value["bg-color"],
					borderWidth: 1
				},
				data: sizeData
			}
		]
	}
}

watch(indices, () => {
	if (chartCtx.value) {
		chartCtx.value.setOption(getOptions())
	}
})

watch(style, () => {
	if (chartCtx.value) {
		chartCtx.value.setOption(getOptions())
	}
})

onMounted(() => {
	const chartDom = document.getElementById("top-indices-chart")

	echartsUse([
		TooltipComponent,
		LegendComponent,
		GridComponent,
		PieChart,
		CanvasRenderer // If you only need to use the canvas rendering mode, the bundle will not include the SVGRenderer module, which is not needed.
	])

	chartCtx.value = echartsInit(chartDom)

	chartCtx.value.setOption(getOptions())

	if (chartDom) {
		new ResizeObserver(() => {
			if (chartCtx.value) {
				chartCtx.value.resize()
			}
		}).observe(chartDom)
	}
})
</script>

<style lang="scss" scoped>
.top-indices-chart-container {
	width: 100%;
	overflow: hidden;
	box-sizing: border-box;
}
</style>
