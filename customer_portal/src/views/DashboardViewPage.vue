<template>
	<div class="min-h-screen bg-gray-50">
		<!-- Header -->
		<header class="border-b bg-white shadow-sm">
			<div class="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
				<div class="flex h-16 justify-between">
					<div class="flex items-center">
						<div class="mr-3 min-h-8">
							<img
								v-if="portalLogo && showLogo"
								class="h-8 w-auto"
								:src="portalLogo"
								:alt="portalTitle"
								@error="showLogo = false"
							/>
						</div>
						<h1 class="text-xl font-semibold text-gray-900">{{ portalTitle }}</h1>
						<nav class="ml-8 flex space-x-8">
							<router-link
								to="/"
								class="rounded-md px-3 py-2 text-sm font-medium text-gray-500 hover:text-gray-900"
							>
								Overview
							</router-link>
							<router-link
								to="/alerts"
								class="rounded-md px-3 py-2 text-sm font-medium text-gray-500 hover:text-gray-900"
							>
								Alerts
							</router-link>
							<router-link
								to="/cases"
								class="rounded-md px-3 py-2 text-sm font-medium text-gray-500 hover:text-gray-900"
							>
								Cases
							</router-link>
							<router-link
								to="/agents"
								class="rounded-md px-3 py-2 text-sm font-medium text-gray-500 hover:text-gray-900"
							>
								Agents
							</router-link>
							<router-link
								to="/event-search"
								class="rounded-md px-3 py-2 text-sm font-medium text-gray-500 hover:text-gray-900"
							>
								Event Search
							</router-link>
							<router-link
								to="/dashboards"
								class="rounded-md border-b-2 border-indigo-600 px-3 py-2 text-sm font-medium text-indigo-600"
							>
								Dashboards
							</router-link>
						</nav>
					</div>
					<div class="flex items-center space-x-4">
						<div class="text-sm text-gray-700">
							Welcome,
							<span class="font-medium">{{ username }}</span>
						</div>
						<button
							@click="logout"
							class="rounded-md bg-red-600 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-red-700"
						>
							Logout
						</button>
					</div>
				</div>
			</div>
		</header>

		<!-- Main Content -->
		<div class="mx-auto max-w-7xl px-4 py-6 sm:px-6 lg:px-8">
			<!-- Dashboard Header Bar -->
			<div class="mb-6 rounded-lg bg-white shadow">
				<div class="px-4 py-4 sm:px-6">
					<div class="flex flex-wrap items-center justify-between gap-4">
						<div class="flex items-center gap-3">
							<button
								@click="router.push('/dashboards')"
								class="rounded-md p-1.5 text-gray-400 hover:bg-gray-100 hover:text-gray-600"
							>
								<svg class="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
									<path
										stroke-linecap="round"
										stroke-linejoin="round"
										stroke-width="2"
										d="M10 19l-7-7m0 0l7-7m-7 7h18"
									/>
								</svg>
							</button>
							<div>
								<h2 class="text-lg font-semibold text-gray-900">
									{{ dashboardTitle || "Loading..." }}
								</h2>
								<p class="text-sm text-gray-500">{{ dashboardDescription }}</p>
							</div>
						</div>
						<div class="flex items-center gap-2">
							<button
								v-for="preset in timePresets"
								:key="preset.value"
								@click="selectTimerange(preset.value)"
								class="rounded-md px-3 py-1.5 text-sm font-medium transition-colors"
								:class="
									selectedTimerange === preset.value
										? 'bg-indigo-600 text-white'
										: 'bg-gray-100 text-gray-700 hover:bg-gray-200'
								"
							>
								{{ preset.label }}
							</button>
							<button
								@click="fetchPanelData"
								:disabled="loading"
								class="ml-2 rounded-md bg-gray-100 p-1.5 text-gray-600 hover:bg-gray-200 disabled:opacity-50"
							>
								<svg
									class="h-4 w-4"
									:class="{ 'animate-spin': loading }"
									fill="none"
									stroke="currentColor"
									viewBox="0 0 24 24"
								>
									<path
										stroke-linecap="round"
										stroke-linejoin="round"
										stroke-width="2"
										d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"
									/>
								</svg>
							</button>
						</div>
					</div>
				</div>
			</div>

			<!-- Error -->
			<div v-if="errorMsg" class="mb-6 rounded-md border border-red-300 bg-red-50 p-4">
				<p class="text-sm text-red-700">{{ errorMsg }}</p>
			</div>

			<!-- Loading -->
			<div v-if="loading && !hasData" class="rounded-lg bg-white px-4 py-12 text-center shadow">
				<div class="mx-auto h-8 w-8 animate-spin rounded-full border-b-2 border-indigo-600"></div>
				<p class="mt-2 text-sm text-gray-500">Loading dashboard panels...</p>
			</div>

			<!-- Panels Grid -->
			<div v-if="hasData || (!loading && panels.length > 0)" class="panel-grid">
				<div v-for="panel in panels" :key="panel.id" :style="{ gridColumn: `span ${panel.w}` }">
					<!-- Stat Panel -->
					<div
						v-if="panel.type === 'stat'"
						class="cursor-pointer rounded-lg bg-white p-6 text-center shadow transition-shadow hover:shadow-md"
						@click="openEventSearch(panel.lucene || '*')"
					>
						<p class="text-xs font-medium tracking-wide text-gray-500 uppercase">{{ panel.title }}</p>
						<p class="mt-2 text-3xl font-bold" :style="{ color: accentColor }">
							{{ formatStatValue(panelResults[panel.id]?.value) }}
						</p>
						<p v-if="panelResults[panel.id]?.error" class="mt-1 text-xs text-red-500">
							{{ panelResults[panel.id].error }}
						</p>
					</div>

					<!-- Chart Panel -->
					<div v-else class="rounded-lg bg-white shadow">
						<div class="border-b border-gray-100 px-4 py-3">
							<h3 class="text-sm font-medium text-gray-700">{{ panel.title }}</h3>
						</div>
						<div class="p-2">
							<div :id="`chart-${panel.id}`" :style="{ height: `${panel.h}px`, width: '100%' }"></div>
						</div>
						<p v-if="panelResults[panel.id]?.error" class="px-4 pb-2 text-xs text-red-500">
							{{ panelResults[panel.id].error }}
						</p>
					</div>
				</div>
			</div>
		</div>
	</div>
</template>

<script setup lang="ts">
import type { ECharts } from "echarts/core"
import type { DashboardPanel, PanelResult } from "@/api/siem"
import { ref, computed, onMounted, onBeforeUnmount, nextTick, watch } from "vue"
import { useRoute, useRouter } from "vue-router"
import { usePortalSettingsStore } from "@/stores/portalSettings"
import { SiemAPI } from "@/api/siem"
import { BarChart, LineChart, PieChart } from "echarts/charts"
import { GridComponent, LegendComponent, TooltipComponent } from "echarts/components"
import { init as echartsInit, use as echartsUse } from "echarts/core"
import { CanvasRenderer } from "echarts/renderers"

echartsUse([TooltipComponent, LegendComponent, GridComponent, PieChart, BarChart, LineChart, CanvasRenderer])

const route = useRoute()
const router = useRouter()
const portalSettingsStore = usePortalSettingsStore()

const showLogo = ref(true)

const username = computed(() => {
	try {
		const user = JSON.parse(localStorage.getItem("customer-portal-user") || "{}")
		return user.username || "User"
	} catch {
		return "User"
	}
})
const portalTitle = computed(() => portalSettingsStore.portalTitle || "Customer Portal")
const portalLogo = computed(() => portalSettingsStore.portalLogo)

function logout() {
	localStorage.removeItem("customer-portal-auth-token")
	localStorage.removeItem("customer-portal-user")
	router.push("/login")
}

// -- Dashboard state --
const dashboardId = computed(() => Number(route.params.id))

const COLORS = [
	"#6366f1",
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

const accentColor = ref("#6366f1")
const customerCode = ref("")
const sourceName = ref("")
const dashboardTitle = ref("")
const dashboardDescription = ref("")
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
let resizeObservers: ResizeObserver[] = []

function formatStatValue(value: number | null | undefined): string {
	if (value == null) return "—"
	if (value >= 1_000_000) return `${(value / 1_000_000).toFixed(1)}M`
	if (value >= 1_000) return `${(value / 1_000).toFixed(1)}K`
	return value.toLocaleString()
}

function selectTimerange(value: string) {
	selectedTimerange.value = value
	fetchPanelData()
}

// -- Drill-down to Event Search --
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

// -- Fetch panel data --
async function fetchPanelData() {
	loading.value = true
	errorMsg.value = ""
	try {
		const res = await SiemAPI.getPanelData(dashboardId.value, selectedTimerange.value)
		if (res.success) {
			const tpl = res.template
			dashboardTitle.value = tpl.title
			dashboardDescription.value = tpl.description
			panels.value = tpl.panels
			accentColor.value = res.accent_color || "#6366f1"
			customerCode.value = res.customer_code
			sourceName.value = res.source_name
			panelResults.value = res.panels
			await nextTick()
			renderAllCharts()
		} else {
			errorMsg.value = res.message || "Failed to fetch panel data"
		}
	} catch (err: any) {
		errorMsg.value = err.response?.data?.detail || err.message || "Failed to fetch panel data"
	} finally {
		loading.value = false
	}
}

// -- ECharts options builders --
function getHistogramOptions(result: PanelResult) {
	return {
		tooltip: { trigger: "axis", axisPointer: { type: "shadow" } },
		grid: { left: 50, right: 20, top: 10, bottom: 30 },
		xAxis: {
			type: "category",
			data: result.labels,
			axisLabel: { color: "#6b7280", fontSize: 10, rotate: result.labels.length > 20 ? 45 : 0 },
			axisLine: { lineStyle: { color: "#e5e7eb" } }
		},
		yAxis: {
			type: "value",
			axisLabel: { color: "#6b7280", fontSize: 10 },
			splitLine: { lineStyle: { color: "#f3f4f6" } }
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

function getPieOptions(result: PanelResult) {
	const data = result.labels.map((label, i) => ({ value: result.data[i], name: label }))
	return {
		tooltip: { trigger: "item", formatter: "{b}: <strong>{c}</strong> ({d}%)" },
		legend: {
			type: "scroll",
			orient: "vertical",
			right: 10,
			top: 20,
			bottom: 20,
			textStyle: { color: "#374151", fontSize: 11 }
		},
		series: [
			{
				type: "pie",
				radius: ["40%", "70%"],
				center: ["35%", "50%"],
				avoidLabelOverlap: true,
				itemStyle: { borderColor: "#ffffff", borderWidth: 2, borderRadius: 4 },
				label: { show: false },
				color: COLORS,
				data
			}
		]
	}
}

function getBarHOptions(result: PanelResult) {
	return {
		tooltip: { trigger: "axis", axisPointer: { type: "shadow" } },
		grid: { left: 10, right: 30, top: 10, bottom: 10, containLabel: true },
		xAxis: {
			type: "value",
			axisLabel: { color: "#6b7280", fontSize: 10 },
			splitLine: { lineStyle: { color: "#f3f4f6" } }
		},
		yAxis: {
			type: "category",
			data: [...result.labels].reverse(),
			axisLabel: { color: "#6b7280", fontSize: 10, width: 180, overflow: "truncate" },
			axisLine: { lineStyle: { color: "#e5e7eb" } }
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
		chart.on("click", (params: { name?: string }) => {
			if (!params.name) return
			const query = buildDrilldownQuery(panel, params.name)
			if (query) openEventSearch(query)
		})

		const observer = new ResizeObserver(() => chart?.resize())
		observer.observe(dom)
		resizeObservers.push(observer)
	}

	let options
	if (panel.type === "histogram") options = getHistogramOptions(result)
	else if (panel.type === "pie") options = getPieOptions(result)
	else if (panel.type === "bar_h") options = getBarHOptions(result)

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

// -- Lifecycle --
onMounted(() => {
	fetchPanelData()
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
	gap: 16px;
}
</style>
