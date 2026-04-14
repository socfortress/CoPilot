<template>
	<div class="@container flex flex-col gap-8">
		<!-- Header Bar -->
		<div class="flex flex-wrap items-end justify-between gap-6">
			<div class="flex gap-3">
				<n-button quaternary size="small" @click="routeDashboardsList().navigate()">
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
					<n-radio-button v-for="preset in timePresets" :key="preset" :value="preset" :label="preset" />
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
			<CardStats
				v-for="item in panels"
				:key="item.panel.id"
				:title="item.panel.title"
				class="h-full"
				:class="[panelColSpanClass(item.panel.w)]"
				:clickable="['stat'].includes(item.panel.type)"
				@click="['stat'].includes(item.panel.type) ? openEventSearch(item.panel.lucene || '*') : undefined"
			>
				<template v-if="['pie', 'bar_h'].includes(item.panel.type)" #header-extra>
					<n-tooltip class="py1! px2!">
						<template #trigger>
							<Icon :name="InfoIcon" :size="16" class="text-secondary cursor-help" />
						</template>
						<div class="text-sm">Click on a segment to go to the event search page.</div>
					</n-tooltip>
				</template>

				<div v-if="item.panel.type === 'stat'" class="font-mono text-2xl font-semibold">
					{{ formatCompactNumber(item.data?.value) }}
				</div>

				<component
					:is="chartByType[item.panel.type]"
					v-if="item.data && chartByType[item.panel.type]"
					:labels="item.data.labels"
					:data="item.data.data"
					:monochrome="item.panel.type === 'histogram'"
					:labels-datetime="item.panel.type === 'histogram'"
					:height="`${item.panel.type === 'histogram' ? `${item.panel.h + 100}px` : `${item.panel.h}px`}`"
					@item-click="onChartItemClick(item.panel, $event.name)"
				/>

				<span v-if="item.data?.error" class="text-error text-xs">
					{{ item.data.error }}
				</span>
			</CardStats>
		</n-spin>

		<n-empty v-if="!loading && !hasData && errorMsg" :description="errorMsg" />
	</div>
</template>

<script setup lang="ts">
import type { Component } from "vue"
import type { ApiError } from "@/types/common"
import type { DashboardPanel, DashboardPanelType, PanelResult } from "@/types/dashboards.d"
import axios from "axios"
import { NButton, NEmpty, NRadioButton, NRadioGroup, NSpin, NTooltip, useMessage } from "naive-ui"
import { computed, ref, watch } from "vue"
import Api from "@/api"
import CardStats from "@/components/common/cards/CardStats.vue"
import ChartBar from "@/components/common/charts/ChartBar.vue"
import ChartColumn from "@/components/common/charts/ChartColumn.vue"
import ChartPie from "@/components/common/charts/ChartPie.vue"
import Icon from "@/components/common/Icon.vue"
import { useNavigation } from "@/composables/common/useNavigation"
import { formatCompactNumber, getApiErrorMessage } from "@/utils"
import { panelColSpanClass } from "./utils"

const { dashboardId } = defineProps<{
	dashboardId: number
}>()

const ArrowBackIcon = "carbon:arrow-left"
const RefreshIcon = "carbon:renew"

interface DashboardPanelEntry {
	panel: DashboardPanel
	data: PanelResult | undefined
}

const chartByType: Record<DashboardPanelType, Component | undefined> = {
	stat: undefined,
	pie: ChartPie,
	bar_h: ChartBar,
	histogram: ChartColumn
}

const { routeDashboardsList, routeEventSearch } = useNavigation()
const InfoIcon = "carbon:information"
const message = useMessage()

const timePresets = ["1h", "6h", "24h", "7d", "30d"]

const dashboardTitle = ref("")
const dashboardDescription = ref("")
const customerCode = ref("")
const sourceName = ref("")
const panels = ref<DashboardPanelEntry[]>([])
const loading = ref(false)
const errorMsg = ref("")
const selectedTimerange = ref(timePresets[2])

const hasData = computed(() => panels.value.some(row => row.data != null))

let abortController = new AbortController()

async function fetchPanelData() {
	if (abortController) {
		abortController.abort()
	}

	abortController = new AbortController()

	loading.value = true
	errorMsg.value = ""

	try {
		const res = await Api.siem.getPanelData(dashboardId, selectedTimerange.value, abortController.signal)

		if (res.data.success) {
			dashboardTitle.value = res.data.template.title
			dashboardDescription.value = res.data.template.description

			panels.value = res.data.template.panels.map(p => ({
				panel: p,
				data: res.data.panels[p.id]
			}))

			customerCode.value = res.data.customer_code
			sourceName.value = res.data.source_name
		} else {
			errorMsg.value = res.data.message || "Failed to fetch panel data"
			message.error(errorMsg.value)
		}

		loading.value = false
	} catch (error) {
		if (!axios.isCancel(error)) {
			loading.value = false
			errorMsg.value = getApiErrorMessage(error as ApiError) || "Failed to fetch panel data"
			message.error(errorMsg.value)
		}
	}
}

function openEventSearch(luceneQuery: string) {
	routeEventSearch({
		customer_code: customerCode.value,
		source_name: sourceName.value,
		query: luceneQuery
	}).navigate()
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

watch(
	selectedTimerange,
	() => {
		fetchPanelData()
	},
	{ immediate: true }
)
</script>
