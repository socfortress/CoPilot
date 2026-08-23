<template>
	<div class="@container flex flex-col gap-4">
		<div class="flex flex-wrap items-center justify-between gap-3">
			<div class="text-secondary text-sm">
				Live data from
				<strong>{{ sourceName || "the selected event source" }}</strong>
			</div>
			<div class="flex items-center gap-2">
				<n-radio-group v-model:value="selectedTimerange" size="small">
					<n-radio-button v-for="preset in timePresets" :key="preset" :value="preset" :label="preset" />
				</n-radio-group>
				<n-button size="small" :loading @click="fetchPreview()">
					<template #icon>
						<Icon :name="RefreshIcon" :size="16" />
					</template>
				</n-button>
			</div>
		</div>

		<n-spin :show="loading" content-class="grid grid-cols-12 gap-4">
			<CardEntity
				v-for="item in entries"
				:key="item.panel.id"
				size="small"
				class="h-full"
				:class="[panelColSpanClass(item.panel.w)]"
			>
				<template #headerMain>{{ item.panel.title }}</template>
				<template #default>
					<div v-if="item.panel.type === 'stat'" class="font-mono text-2xl font-semibold">
						{{ formatCompactNumber(item.data?.value) }}
					</div>

					<PanelTable
						v-else-if="item.panel.type === 'table'"
						:columns="item.data?.columns"
						:rows="item.data?.rows"
						:height="item.panel.h"
					/>

					<component
						:is="chartByType[item.panel.type]"
						v-else-if="item.data && chartByType[item.panel.type]"
						:labels="item.data.labels"
						:data="item.data.data"
						:monochrome="item.panel.type === 'histogram'"
						:labels-datetime="item.panel.type === 'histogram'"
						:height="`${item.panel.type === 'histogram' ? item.panel.h + 100 : item.panel.h}px`"
					/>

					<span v-if="item.data?.error" class="text-error text-xs">{{ item.data.error }}</span>
				</template>
			</CardEntity>
		</n-spin>

		<n-empty v-if="!loading && errorMsg" :description="errorMsg" />
	</div>
</template>

<script setup lang="ts">
import type { Component } from "vue"
import type { ApiError } from "@/types/common"
import type { CustomDashboardPanel, DashboardPanelType, PanelResult } from "@/types/dashboards"
import axios from "axios"
import { NButton, NEmpty, NRadioButton, NRadioGroup, NSpin, useMessage } from "naive-ui"
import { onBeforeUnmount, ref, watch } from "vue"
import Api from "@/api"
import CardEntity from "@/components/common/cards/CardEntity.vue"
import ChartBar from "@/components/common/charts/ChartBar.vue"
import ChartColumn from "@/components/common/charts/ChartColumn.vue"
import ChartPie from "@/components/common/charts/ChartPie.vue"
import Icon from "@/components/common/Icon.vue"
import { formatCompactNumber, getApiErrorMessage } from "@/utils"
import PanelTable from "../PanelTable.vue"
import { panelColSpanClass } from "../utils"

const { eventSourceId, panels, defaultQuery } = defineProps<{
	eventSourceId: number
	panels: CustomDashboardPanel[]
	defaultQuery: string
}>()

const RefreshIcon = "carbon:renew"

interface PreviewEntry {
	panel: CustomDashboardPanel
	data: PanelResult | undefined
}

const chartByType: Record<DashboardPanelType, Component | undefined> = {
	stat: undefined,
	table: undefined,
	pie: ChartPie,
	bar_h: ChartBar,
	histogram: ChartColumn
}

const message = useMessage()
const timePresets = ["1h", "6h", "24h", "7d", "30d"]

const selectedTimerange = ref(timePresets[2])
const entries = ref<PreviewEntry[]>([])
const sourceName = ref("")
const loading = ref(false)
const errorMsg = ref("")

let abortController = new AbortController()

async function fetchPreview() {
	abortController.abort()
	abortController = new AbortController()

	loading.value = true
	errorMsg.value = ""

	try {
		const res = await Api.siem.previewCustomDashboard(
			{
				event_source_id: eventSourceId,
				default_query: defaultQuery || "*",
				panels,
				timerange: selectedTimerange.value
			},
			abortController.signal
		)

		if (res.data.success) {
			sourceName.value = res.data.source_name
			// The backend fills in the panel ids it generated, so read the panel
			// list back from the response instead of the local (id-less) draft.
			entries.value = res.data.template.panels.map(panel => ({
				panel,
				data: res.data.panels[panel.id]
			}))
		} else {
			errorMsg.value = res.data.message || "Failed to generate the preview"
			message.error(errorMsg.value)
		}
		loading.value = false
	} catch (error) {
		if (!axios.isCancel(error)) {
			loading.value = false
			errorMsg.value = getApiErrorMessage(error as ApiError) || "Failed to generate the preview"
			message.error(errorMsg.value)
		}
	}
}

watch(selectedTimerange, () => fetchPreview(), { immediate: true })

// Cancel anything still in flight when this component goes away: without it the
// request outlives the view — the backend keeps working for a page nobody is
// looking at, and the response resolves into a destroyed scope (#1072).
onBeforeUnmount(() => {
	abortController?.abort()
})
</script>
