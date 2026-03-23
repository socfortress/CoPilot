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
		<n-spin :show="loading" content-class="grid grid-cols-12 gap-4">
			<div v-for="item in panels" :key="item.panel.id" :style="{ gridColumn: `span ${item.panel.w}` }">
				<!-- Stat Panel -->
				<CardLink
					v-if="item.panel.type === 'stat'"
					:title="item.panel.title"
					clickable
					class="h-full"
					@click="openEventSearch(item.panel.lucene || '*')"
				>
					<div class="font-mono text-2xl font-semibold">
						{{ formatCompactNumber(item.data?.value) }}
					</div>
					<span v-if="item.data?.error" class="text-error text-xs">
						{{ item.data.error }}
					</span>
				</CardLink>

				<!-- Chart Panel -->
				<CardLink v-else :title="item.panel.title" class="h-full">
					<component
						:is="chartByType[item.panel.type]"
						v-if="item.data && chartByType[item.panel.type]"
						:labels="item.data.labels"
						:data="item.data.data"
						:height="item.panel.h"
						:accent-color
						@item-click="onChartItemClick(item.panel, $event.name)"
					/>
					<span v-if="item.data?.error" class="text-error text-xs">
						{{ item.data.error }}
					</span>
				</CardLink>
			</div>

			<n-empty v-if="!loading && !hasData && errorMsg" :description="errorMsg" />
		</n-spin>
	</div>
</template>

<script setup lang="ts">
import type { Component } from "vue"
import type { DashboardPanel, PanelResult } from "@/types/dashboards.d"
import { NButton, NEmpty, NRadioButton, NRadioGroup, NSpin, useMessage } from "naive-ui"
import { computed, onMounted, ref, watch } from "vue"
import { useRouter } from "vue-router"
import Api from "@/api"
import CardLink from "@/components/common/cards/CardLink.vue"
import ChartBar from "@/components/common/charts/ChartBar.vue"
import ChartHistogram from "@/components/common/charts/ChartHistogram.vue"
import ChartPie from "@/components/common/charts/ChartPie.vue"
import Icon from "@/components/common/Icon.vue"
import { formatCompactNumber } from "@/utils"

const props = defineProps<{
	dashboardId: number
}>()
const ArrowBackIcon = "carbon:arrow-left"
const RefreshIcon = "carbon:renew"

interface DashboardPanelEntry {
	panel: DashboardPanel
	data: PanelResult | undefined
}

const chartByType: Record<string, Component> = {
	pie: ChartPie,
	bar_h: ChartBar,
	histogram: ChartHistogram
}

const router = useRouter()
const message = useMessage()

const COLORS = [
	"#ffffff",
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

const accentColor = ref(COLORS[0])
const dashboardTitle = ref("")
const dashboardDescription = ref("")
const customerCode = ref("")
const sourceName = ref("")
const panels = ref<DashboardPanelEntry[]>([])
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

const hasData = computed(() => panels.value.some(row => row.data != null))

async function fetchPanelData() {
	loading.value = true
	errorMsg.value = ""
	try {
		const res = await Api.siem.getPanelData(props.dashboardId, selectedTimerange.value)
		if (res.data.success) {
			const tpl = res.data.template
			dashboardTitle.value = tpl.title
			dashboardDescription.value = tpl.description
			panels.value = tpl.panels.map(p => ({
				panel: p,
				data: res.data.panels[p.id]
			}))
			accentColor.value = res.data.accent_color || COLORS[0]
			customerCode.value = res.data.customer_code
			sourceName.value = res.data.source_name
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
		// TODO-FE: use router by name
		path: "/event-search",
		query: {
			customer_code: customerCode.value,
			source_name: sourceName.value,
			query: luceneQuery
		}
	})
	window.open(routeData.href, "_blank")
}

function buildDrillDownQuery(panel: DashboardPanel, clickedValue: string): string {
	const baseLucene = panel.lucene && panel.lucene !== "*" ? `(${panel.lucene})` : ""
	const fieldFilter = panel.field ? `${panel.field}:"${clickedValue}"` : ""
	return [baseLucene, fieldFilter].filter(Boolean).join(" AND ")
}

function onChartItemClick(panel: DashboardPanel, name: string) {
	if (panel.type === "histogram") {
		return
	}
	const query = buildDrillDownQuery(panel, name)
	if (query) openEventSearch(query)
}

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

onMounted(() => {
	loadTemplate()
})
</script>
