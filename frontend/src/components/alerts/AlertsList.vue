<template>
	<div class="alerts-list">
		<div class="header flex items-center justify-end gap-2">
			<div class="info flex grow gap-5">
				<n-popover overlap placement="bottom-start">
					<template #trigger>
						<div class="bg-default rounded-default">
							<n-button size="small" class="!cursor-help">
								<template #icon>
									<Icon :name="InfoIcon"></Icon>
								</template>
							</n-button>
						</div>
					</template>
					<div class="flex flex-col gap-2">
						<div class="box">
							Total Summaries:
							<code>{{ totalAlertsSummary }}</code>
						</div>
						<div class="box">
							Total Alerts:
							<code>{{ totalAlerts }}</code>
						</div>
					</div>
				</n-popover>
			</div>
			<div class="actions flex items-center gap-2">
				<n-button v-if="!isFilterPreselected" size="small" @click="(showStatsDrawer = true)">
					<template #icon>
						<Icon :name="StatsIcon" :size="14"></Icon>
					</template>
					Stats
				</n-button>
				<n-button size="small" @click="(showFiltersDrawer = true)">
					<template #icon>
						<Icon :name="FilterIcon" :size="15"></Icon>
					</template>
					Filters
				</n-button>
				<ThreatIntelButton size="small" type="primary" />
			</div>
		</div>
		<n-spin :show="loading">
			<template #description>Alerts are being fetched, this may take up to 1 minute.</template>

			<div class="my-3 flex min-h-52 flex-col gap-2">
				<template v-if="alertsSummaryList.length">
					<AlertsSummaryItem
						v-for="alertsSummary of alertsSummaryList"
						:key="alertsSummary.index_name"
						:alerts-summary="alertsSummary"
						class="item-appear item-appear-bottom item-appear-005"
					/>
				</template>
				<template v-else>
					<n-empty v-if="!loading" description="No items found" class="h-48 justify-center" />
				</template>
			</div>
		</n-spin>

		<n-drawer
			v-model:show="showStatsDrawer"
			:width="700"
			style="max-width: 90vw"
			:trap-focus="false"
			display-directive="show"
		>
			<n-drawer-content title="Alerts stats" closable body-content-style="padding:0" :native-scrollbar="false">
				<AlertsStats :filters="filters" @mounted="(alertsStatsCTX = $event)" />
			</n-drawer-content>
		</n-drawer>

		<n-drawer
			v-model:show="showFiltersDrawer"
			display-directive="show"
			:trap-focus="false"
			style="max-width: 90vw; width: 500px"
			:show-mask="loadingFilters ? 'transparent' : undefined"
			:class="{ 'opacity-0': loadingFilters }"
		>
			<n-drawer-content title="Alerts filters" closable :native-scrollbar="false">
				<AlertsFilters :filters="filters" @search="startSearch(true)">
					<div v-if="!isFilterPreselected" class="mb-6">
						<n-select
							v-model:value="filterType"
							:options="[
								{
									label: 'Filter by Agent Hostname',
									value: 'agentHostname'
								},
								{
									label: 'Filter by Index name',
									value: 'indexName'
								}
							]"
							placeholder="Filter by Agent or Index"
							clearable
							@update:value="
								() => {
									filters.agentHostname = undefined
									filters.indexName = undefined
								}
							"
						/>
						<n-select
							v-if="filterType === 'agentHostname'"
							v-model:value="filters.agentHostname"
							:options="agentHostnameOptions"
							placeholder="Agents list"
							clearable
							filterable
							:loading="loadingAgents"
							class="mt-2"
						/>
						<n-select
							v-if="filterType === 'indexName'"
							v-model:value="filters.indexName"
							:options="indexNameOptions"
							clearable
							filterable
							placeholder="Indices list"
							:loading="loadingIndex"
							class="mt-2"
						/>
					</div>
				</AlertsFilters>
			</n-drawer-content>
		</n-drawer>
	</div>
</template>

<script setup lang="ts">
// MOCK
// import { alerts_summary } from "./mock"
// import type { AlertsSummary } from "@/types/alerts.d"

import type { AlertsSummaryQuery } from "@/api/endpoints/alerts"
import type { Agent } from "@/types/agents.d"
import type { IndexStats } from "@/types/indices.d"
import Api from "@/api"
import Icon from "@/components/common/Icon.vue"
import axios from "axios"
import { NButton, NDrawer, NDrawerContent, NEmpty, NPopover, NSelect, NSpin, useMessage } from "naive-ui"
import { computed, defineAsyncComponent, nextTick, onBeforeMount, onBeforeUnmount, onMounted, ref, toRefs } from "vue"
import AlertsFilters from "./AlertsFilters.vue"
import AlertsStats, { type AlertsStatsCTX } from "./AlertsStats.vue"
import AlertsSummaryItem, { type AlertsSummaryExt } from "./AlertsSummary.vue"

const props = defineProps<{ agentHostname?: string; indexName?: string }>()

const ThreatIntelButton = defineAsyncComponent(() => import("@/components/threatIntel/ThreatIntelButton.vue"))

const { agentHostname, indexName } = toRefs(props)

const message = useMessage()
const loadingIndex = ref(false)
const loadingAgents = ref(false)
const loading = ref(false)
const indices = ref<IndexStats[]>([])
const agents = ref<Agent[]>([])
const alertsSummaryList = ref<AlertsSummaryExt[]>([])
const loadingFilters = ref(true)
const showFiltersDrawer = ref(true)
const showStatsDrawer = ref(false)
let abortController: AbortController | null = null

const InfoIcon = "carbon:information"
const FilterIcon = "carbon:filter-edit"
const StatsIcon = "carbon:chart-column"

const alertsStatsCTX = ref<AlertsStatsCTX | null>(null)

const totalAlertsSummary = computed<number>(() => {
	return alertsSummaryList.value.length || 0
})
const totalAlerts = computed<number>(() => {
	return alertsSummaryList.value.reduce((acc: number, val: AlertsSummaryExt) => {
		return acc + val.alerts.length
	}, 0)
})

const filters = ref<AlertsSummaryQuery>({})

const filterType = ref<string | null>(null)

const isFilterPreselected = computed(() => {
	return !!agentHostname?.value || !!indexName?.value
})

const agentHostnameOptions = computed(() => {
	if (agentHostname?.value) {
		return [{ value: agentHostname.value, label: agentHostname.value }]
	}
	return (agents.value || []).map(o => ({ value: o.hostname, label: o.hostname }))
})

const indexNameOptions = computed(() => {
	if (indexName?.value) {
		return [{ value: indexName.value, label: indexName.value }]
	}
	return (indices.value || []).map(o => ({ value: o.index, label: o.index }))
})

function addIndexInfo() {
	if (indices.value?.length && alertsSummaryList.value.length) {
		for (const alert of alertsSummaryList.value) {
			const index = indices.value.find(o => o.index === alert.index_name)
			alert.indexStats = index
		}
	}
}

function getData() {
	loading.value = true

	abortController = new AbortController()

	Api.alerts
		.getAll(filters.value, abortController.signal)
		.then(res => {
			alertsSummaryList.value = res.data?.alerts_summary || []

			if (res.data.success) {
				nextTick(() => {
					addIndexInfo()
				})
			} else {
				message.warning(res.data?.message || "An error occurred. Please try again later.")
			}
		})
		.catch(err => {
			if (!axios.isCancel(err)) {
				alertsSummaryList.value = []

				message.error(err.response?.data?.message || "An error occurred. Please try again later.")
			}
		})
		.finally(() => {
			loading.value = false
		})
}

function getIndices() {
	loadingIndex.value = true

	Api.indices
		.getIndices()
		.then(res => {
			if (res.data.success) {
				indices.value = res.data.indices_stats || []

				nextTick(() => {
					addIndexInfo()
				})
			} else {
				message.error(res.data?.message || "An error occurred. Please try again later.")
			}
		})
		.catch(err => {
			if (err.response?.status === 401) {
				message.error(
					err.response?.data?.message ||
						"Wazuh-Indexer returned Unauthorized. Please check your connector credentials."
				)
			} else if (err.response?.status === 404) {
				message.error(err.response?.data?.message || "No indices were found.")
			} else {
				message.error(err.response?.data?.message || "An error occurred. Please try again later.")
			}
		})
		.finally(() => {
			loadingIndex.value = false
		})
}

function getAgents() {
	loadingAgents.value = true

	Api.agents
		.getAgents()
		.then(res => {
			if (res.data.success) {
				agents.value = res.data.agents || []
			} else {
				message.error(res.data?.message || "An error occurred. Please try again later.")
			}
		})
		.catch(err => {
			message.error(err.response?.data?.message || "An error occurred. Please try again later.")
		})
		.finally(() => {
			loadingAgents.value = false
		})
}

function getStatsFiltersString() {
	return [filters.value.alertField, filters.value.alertValue, filters.value.maxAlerts, filters.value.timerange].join(
		","
	)
}

let lastStatsFilters = ""

function startSearch(closeDrawer?: boolean) {
	cancelSearch()

	setTimeout(() => {
		getData()

		const statsFiltersString = getStatsFiltersString()
		if (lastStatsFilters !== statsFiltersString) {
			alertsStatsCTX.value?.startSearch()
			lastStatsFilters = statsFiltersString
		}
	}, 200)

	if (closeDrawer) {
		showFiltersDrawer.value = false
	}
}

function cancelSearch() {
	abortController?.abort()
}

onBeforeMount(() => {
	if (agentHostname?.value) {
		filters.value.agentHostname = agentHostname.value
	}
	if (indexName?.value) {
		filters.value.indexName = indexName.value
	}

	nextTick(() => {
		if (!isFilterPreselected.value) {
			getAgents()
			getIndices()
		}

		// MOCK
		// alertsSummaryList.value = alerts_summary as AlertsSummary[]
		startSearch()
	})
})

onMounted(() => {
	showFiltersDrawer.value = false

	setTimeout(() => {
		loadingFilters.value = false
	}, 1000)
})

onBeforeUnmount(() => {
	cancelSearch()
})
</script>
