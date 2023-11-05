<template>
	<div class="alerts-list">
		<div class="header flex items-center justify-end gap-2" ref="header">
			<div class="info grow flex gap-5">
				<n-popover overlap placement="bottom-start">
					<template #trigger>
						<div class="bg-color border-radius">
							<n-button size="small" class="!cursor-help">
								<template #icon>
									<Icon :name="InfoIcon"></Icon>
								</template>
							</n-button>
						</div>
					</template>
					<div class="flex flex-col gap-2">
						<div class="box">
							Total Items:
							<code>{{ totalAlertsSummary }}</code>
						</div>
						<div class="box">
							Total Alerts:
							<code>{{ totalAlerts }}</code>
						</div>
					</div>
				</n-popover>
			</div>
			<div class="actions flex gap-2 items-center">
				<n-button size="small" @click="showStatsDrawer = true">
					<template #icon>
						<Icon :name="StatsIcon" :size="14"></Icon>
					</template>
					Stats
				</n-button>
				<n-button size="small" @click="showFiltersDrawer = true">
					<template #icon>
						<Icon :name="FilterIcon" :size="15"></Icon>
					</template>
					Filters
				</n-button>
			</div>
		</div>
		<n-spin :show="loading">
			<template #description>Alerts are being fetched, this may take up to 1 minute.</template>

			<div class="list my-3">
				<template v-if="alertsSummaryList.length">
					<AlertsSummaryItem
						v-for="alertsSummary of alertsSummaryList"
						:key="alertsSummary.index_name"
						:alertsSummary="alertsSummary"
					/>
				</template>
				<template v-else>
					<n-empty description="No items found" v-if="!loading" />
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
			<n-drawer-content title="Alerts stats" closable body-content-style="padding:0">
				<div class="stats flex gap-2">stats...</div>
			</n-drawer-content>
		</n-drawer>

		<n-drawer v-model:show="showFiltersDrawer" display-directive="show" style="max-width: 90vw; width: 500px">
			<n-drawer-content title="Alerts filters" closable :native-scrollbar="false">
				<AlertsFilters :filters="filters">
					<div class="flex gap-2">
						<n-form-item label="Agent" class="basis-1/2">
							<n-select
								v-model:value="filters.agentHostname"
								:options="agentHostnameOptions"
								placeholder="Agents list"
								clearable
								:loading="loadingAgents"
							/>
						</n-form-item>
						<n-form-item label="Index" class="basis-1/2">
							<n-select
								v-model:value="filters.indexName"
								:options="indexNameOptions"
								clearable
								filterable
								placeholder="Indices list"
								:loading="loadingIndex"
							/>
						</n-form-item>
					</div>
				</AlertsFilters>
			</n-drawer-content>
		</n-drawer>
	</div>
</template>

<script setup lang="ts">
import { ref, onBeforeMount, toRefs, computed } from "vue"
import { useMessage, NSpin, NPopover, NButton, NEmpty, NDrawer, NDrawerContent, NFormItem, NSelect } from "naive-ui"
import Api from "@/api"
import AlertsFilters from "./AlertsFilters.vue"
import AlertsSummaryItem, { type AlertsSummaryExt } from "./AlertsSummary.vue"
import { useResizeObserver } from "@vueuse/core"
import Icon from "@/components/common/Icon.vue"
import type { AlertsSummary } from "@/types/alerts.d"
import type { AlertsSummaryQuery } from "@/api/alerts"
import { alerts_summary } from "./mock"
import type { IndexStats } from "@/types/indices.d"
import { nextTick } from "vue"
import type { Agent } from "@/types/agents.d"

const props = defineProps<{ agentHostname?: string }>()
const { agentHostname } = toRefs(props)

const message = useMessage()
const loadingIndex = ref(false)
const loadingAgents = ref(false)
const loading = ref(false)
const indices = ref<IndexStats[]>([])
const agents = ref<Agent[]>([])
const alertsSummaryList = ref<AlertsSummaryExt[]>([])
const header = ref()
const showFiltersDrawer = ref(false)
const showStatsDrawer = ref(false)

const InfoIcon = "carbon:information"
const FilterIcon = "carbon:filter-edit"
const StatsIcon = "carbon:chart-column"

const totalAlertsSummary = computed<number>(() => {
	return alertsSummaryList.value.length || 0
})
const totalAlerts = computed<number>(() => {
	return alertsSummaryList.value.reduce((acc: number, val: AlertsSummaryExt) => {
		return acc + val.alerts.length
	}, 0)
})

const filters = ref<AlertsSummaryQuery>({})

const agentHostnameOptions = computed(() => {
	return (agents.value || []).map(o => ({ value: o.hostname, label: o.hostname }))
})

const indexNameOptions = computed(() => {
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

	Api.alerts
		.getAll(filters.value)
		.then(res => {
			if (res.data.success) {
				alertsSummaryList.value = res.data?.alerts_summary || []

				nextTick(() => {
					addIndexInfo()
				})
			} else {
				message.warning(res.data?.message || "An error occurred. Please try again later.")
			}
		})
		.catch(err => {
			message.error(err.response?.data?.message || "An error occurred. Please try again later.")
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
				message.error(err.response?.data?.message || "No alerts were found.")
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

useResizeObserver(header, entries => {
	const entry = entries[0]
	const { width } = entry.contentRect

	console.log(width)
})

/*
watch([currentPage, pageSize, timerange], ([page, pageSize, timerange]) => {
	getData(page, pageSize, timerange)
})
*/
onBeforeMount(() => {
	agentHostname?.value && (filters.value.agentHostname = agentHostname.value)

	alertsSummaryList.value = alerts_summary as AlertsSummary[]
	// getData()

	getIndices()
	getAgents()
})
</script>

<style lang="scss" scoped>
.alerts-list {
	.list {
		container-type: inline-size;
		min-height: 200px;
	}
}
</style>
