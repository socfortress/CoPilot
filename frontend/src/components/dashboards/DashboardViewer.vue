<template>
	<div class="flex flex-col gap-4">
		<!-- Header Bar -->
		<div class="flex flex-wrap items-end justify-between gap-6">
			<div class="flex gap-3">
				<!-- TODO-FE: use router by name -->
				<n-button quaternary size="small" @click="router.push('/dashboards')">
					<template #icon>
						<Icon :name="ArrowBackIcon" :size="22" />
					</template>
				</n-button>
				<div class="flex flex-col">
					<span class="text-lg font-semibold">{{ dashboardTitle }}</span>
					<span class="text-xs opacity-60">{{ dashboardDescription }}</span>
				</div>
			</div>
			<div class="flex grow items-center justify-end gap-2">
				<n-radio-group v-model:value="selectedTimerange" size="small">
					<n-radio-button
						v-for="preset in timePresets"
						:key="preset.value"
						:value="preset.value"
						size="small"
						:label="preset.label"
					/>
				</n-radio-group>

				<n-button size="small" :loading @click="fetchPanelData">
					<template #icon>
						<Icon :name="RefreshIcon" :size="16" />
					</template>
				</n-button>
			</div>
		</div>

		<!-- Panels Grid -->
		<n-spin :show="loading && !hasData">
			<div v-if="hasData || !loading" class="panel-grid">
				<div
					v-for="panel in panels"
					:key="panel.id"
					class="panel-cell"
					:style="{ gridColumn: `span ${panel.w}` }"
				>
					<!-- Stat Panel -->
					<n-card
						v-if="panel.type === 'stat'"
						size="small"
						class="h-full cursor-pointer transition-shadow hover:shadow-md"
						@click="openEventSearch(panel.lucene || '*')"
					>
						<div class="flex h-full flex-col items-center justify-center py-4">
							<span class="text-xs tracking-wide uppercase opacity-60">{{ panel.title }}</span>
							<span class="stat-value" :style="{ color: accentColor }">
								{{ formatCompactNumber(panelResults[panel.id]?.value) }}
							</span>
							<span v-if="panelResults[panel.id]?.error" class="text-xs text-red-400">
								{{ panelResults[panel.id].error }}
							</span>
						</div>
					</n-card>

					<!-- Chart Panel -->
					<n-card v-else size="small" class="h-full">
						<template #header>
							<span class="text-sm">{{ panel.title }}</span>
						</template>
						<div :id="`chart-${panel.id}`" :style="{ height: `${panel.h}px`, width: '100%' }"></div>
						<span v-if="panelResults[panel.id]?.error" class="text-xs text-red-400">
							{{ panelResults[panel.id].error }}
						</span>
					</n-card>
				</div>
			</div>
			<n-empty v-if="!loading && !hasData && errorMsg" :description="errorMsg" />
		</n-spin>
	</div>
</template>

<script setup lang="ts">
import type { ECharts } from "echarts/core"
import type { DashboardPanel, PanelResult } from "@/types/dashboards.d"
import { BarChart, LineChart, PieChart } from "echarts/charts"
import { GridComponent, LegendComponent, TooltipComponent } from "echarts/components"
import { init as echartsInit, use as echartsUse } from "echarts/core"
import { CanvasRenderer } from "echarts/renderers"
import { NButton, NCard, NEmpty, NRadioButton, NRadioGroup, NSpin, useMessage } from "naive-ui"
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from "vue"
import { useRouter } from "vue-router"
import Api from "@/api"
import Icon from "@/components/common/Icon.vue"
import { useThemeStore } from "@/stores/theme"
import { formatCompactNumber } from "@/utils"

const props = defineProps<{
	dashboardId: number
}>()
const ArrowBackIcon = "carbon:arrow-left"
const RefreshIcon = "carbon:renew"

echartsUse([TooltipComponent, LegendComponent, GridComponent, PieChart, BarChart, LineChart, CanvasRenderer])

const router = useRouter()
const message = useMessage()
const style = computed(() => useThemeStore().style)

const COLORS = [
	"#38bdf8",
	"#818cf8",
	"#34d399",
	"#fbbf24",
	"#f87171",
	"#a78bfa",
	"#fb923c",
	"#2dd4bf",
	"#e879f9",
	"#94a3b8"
]

const accentColor = ref("#38bdf8")
const dashboardTitle = ref("")
const dashboardDescription = ref("")
const customerCode = ref("")
const sourceName = ref("")
const panels = ref<DashboardPanel[]>([])
const panelResults = ref<Record<string, PanelResult>>({})
const loading = ref(false)
const errorMsg = ref("")
const selectedTimerange = ref("24h")

const timePresets = [
	{ label: "1h", value: "1h" },
	{ label: "6h", value: "6h" },
	{ label: "24h", value: "24h" },
	{ label: "7d", value: "7d" },
	{ label: "30d", value: "30d" }
]

const hasData = computed(() => Object.keys(panelResults.value).length > 0)

const chartInstances = ref<Map<string, ECharts>>(new Map())
const resizeObservers: ResizeObserver[] = []

async function fetchPanelData() {
	loading.value = true
	errorMsg.value = ""
	try {
		const res = await Api.siem.getPanelData(props.dashboardId, selectedTimerange.value)
		if (res.data.success) {
			// Set template info from response
			const tpl = res.data.template
			dashboardTitle.value = tpl.title
			dashboardDescription.value = tpl.description
			panels.value = tpl.panels
			accentColor.value = res.data.accent_color || "#38bdf8"
			customerCode.value = res.data.customer_code
			sourceName.value = res.data.source_name
			panelResults.value = res.data.panels
			await nextTick()
			renderAllCharts()
		} else {
			errorMsg.value = res.data.message || "Failed to fetch panel data"
			message.error(errorMsg.value)
		}
	} catch {
		errorMsg.value = "Failed to fetch panel data"
		message.error(errorMsg.value)
	} finally {
		loading.value = false
	}
}

function openEventSearch(luceneQuery: string) {
	const routeData = router.resolve({
		path: "/event-search",
		query: {
			customer_code: customerCode.value,
			source_name: sourceName.value,
			query: luceneQuery
		}
	})
	window.open(routeData.href, "_blank")
}

function buildDrilldownQuery(panel: DashboardPanel, clickedValue: string): string {
	const baseLucene = panel.lucene && panel.lucene !== "*" ? `(${panel.lucene})` : ""
	const fieldFilter = panel.field ? `${panel.field}:"${clickedValue}"` : ""
	return [baseLucene, fieldFilter].filter(Boolean).join(" AND ")
}

function getHistogramOptions(_panel: DashboardPanel, result: PanelResult) {
	return {
		tooltip: {
			trigger: "axis",
			axisPointer: { type: "shadow" }
		},
		grid: { left: 50, right: 20, top: 10, bottom: 30 },
		xAxis: {
			type: "category",
			data: result.labels,
			axisLabel: {
				color: style.value["fg-default-color"],
				fontSize: 10,
				rotate: result.labels.length > 20 ? 45 : 0
			},
			axisLine: { lineStyle: { color: `${style.value["fg-default-color"]}33` } }
		},
		yAxis: {
			type: "value",
			axisLabel: { color: style.value["fg-default-color"], fontSize: 10 },
			splitLine: { lineStyle: { color: `${style.value["fg-default-color"]}1a` } }
		},
		series: [
			{
				type: "bar",
				data: result.data,
				itemStyle: { color: accentColor.value, borderRadius: [2, 2, 0, 0] }
			}
		]
	}
}

function getPieOptions(_panel: DashboardPanel, result: PanelResult) {
	const data = result.labels.map((label, i) => ({
		value: result.data[i],
		name: label
	}))
	return {
		tooltip: {
			trigger: "item",
			formatter: "{b}: <strong>{c}</strong> ({d}%)"
		},
		legend: {
			type: "scroll",
			orient: "vertical",
			right: 10,
			top: 20,
			bottom: 20,
			textStyle: { color: style.value["fg-default-color"], fontSize: 11 }
		},
		series: [
			{
				type: "pie",
				radius: ["40%", "70%"],
				center: ["35%", "50%"],
				avoidLabelOverlap: true,
				itemStyle: {
					borderColor: style.value["bg-default-color"],
					borderWidth: 2,
					borderRadius: 4
				},
				label: { show: false },
				color: COLORS,
				data
			}
		]
	}
}

function getBarHOptions(_panel: DashboardPanel, result: PanelResult) {
	return {
		tooltip: {
			trigger: "axis",
			axisPointer: { type: "shadow" }
		},
		grid: { left: 10, right: 30, top: 10, bottom: 10, containLabel: true },
		xAxis: {
			type: "value",
			axisLabel: { color: style.value["fg-default-color"], fontSize: 10 },
			splitLine: { lineStyle: { color: `${style.value["fg-default-color"]}1a` } }
		},
		yAxis: {
			type: "category",
			data: [...result.labels].reverse(),
			axisLabel: {
				color: style.value["fg-default-color"],
				fontSize: 10,
				width: 180,
				overflow: "truncate"
			},
			axisLine: { lineStyle: { color: `${style.value["fg-default-color"]}33` } }
		},
		series: [
			{
				type: "bar",
				data: [...result.data].reverse(),
				itemStyle: { color: accentColor.value, borderRadius: [0, 2, 2, 0] }
			}
		]
	}
}

function renderChart(panel: DashboardPanel) {
	const result = panelResults.value[panel.id]
	if (!result || panel.type === "stat") return

	const dom = document.getElementById(`chart-${panel.id}`)
	if (!dom) return

	let chart = chartInstances.value.get(panel.id)
	if (!chart) {
		chart = echartsInit(dom)
		chartInstances.value.set(panel.id, chart)

		// Click handler for drill-down to Event Search
		chart.on("click", (params: { name?: string; seriesType?: string }) => {
			if (!params.name) return
			const query = buildDrilldownQuery(panel, params.name)
			if (query) openEventSearch(query)
		})

		const observer = new ResizeObserver(() => chart?.resize())
		observer.observe(dom)
		resizeObservers.push(observer)
	}

	let options
	if (panel.type === "histogram") options = getHistogramOptions(panel, result)
	else if (panel.type === "pie") options = getPieOptions(panel, result)
	else if (panel.type === "bar_h") options = getBarHOptions(panel, result)

	if (options) {
		chart.setOption(options, true)
	}
}

function renderAllCharts() {
	for (const panel of panels.value) {
		if (panel.type !== "stat") {
			renderChart(panel)
		}
	}
}

// Fetch template metadata (panels definition) so we know the grid layout
async function loadTemplate() {
	try {
		await fetchPanelData()
	} catch {
		errorMsg.value = "Failed to load dashboard"
	}
}

watch(selectedTimerange, () => {
	fetchPanelData()
})

watch(style, () => {
	renderAllCharts()
})

onMounted(() => {
	loadTemplate()
})

onBeforeUnmount(() => {
	for (const chart of chartInstances.value.values()) {
		chart.dispose()
	}
	for (const obs of resizeObservers) {
		obs.disconnect()
	}
})
</script>

<style scoped>
.panel-grid {
	display: grid;
	grid-template-columns: repeat(12, 1fr);
	gap: 12px;
}

.stat-value {
	font-size: 2.5rem;
	font-weight: 700;
	line-height: 1.2;
	margin-top: 4px;
}
</style>
