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
						class="mb-2"
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
			<n-drawer-content title="Alerts stats" closable body-content-style="padding:0" :native-scrollbar="false">
				<AlertsStats :filters="filters" />
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
import { ref, onBeforeMount, toRefs, computed, nextTick, onMounted } from "vue"
import { useMessage, NSpin, NPopover, NButton, NEmpty, NDrawer, NDrawerContent, NFormItem, NSelect } from "naive-ui"
import Api from "@/api"
import AlertsStats from "./AlertsStats.vue"
import AlertsFilters from "./AlertsFilters.vue"
import AlertsSummaryItem, { type AlertsSummaryExt } from "./AlertsSummary.vue"
import { useResizeObserver, watchDebounced } from "@vueuse/core"
import Icon from "@/components/common/Icon.vue"
import type { AlertsSummaryQuery } from "@/api/alerts"
// import { alerts_summary } from "./mock"
import type { IndexStats } from "@/types/indices.d"
import axios from "axios"
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
const loadingFilters = ref(true)
const showFiltersDrawer = ref(true)
const showStatsDrawer = ref(false)
let abortController: AbortController | null = null

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

useResizeObserver(header, entries => {
	const entry = entries[0]
	const { width } = entry.contentRect

	console.log(width)
})

watchDebounced(
	filters,
	() => {
		abortController?.abort()

		setTimeout(() => {
			getData()
		}, 200)
	},
	{ deep: true, debounce: 500, maxWait: 1000 }
)

onBeforeMount(() => {
	agentHostname?.value && (filters.value.agentHostname = agentHostname.value)

	getIndices()
	getAgents()

	// alertsSummaryList.value = alerts_summary as AlertsSummary[]
	setTimeout(() => {
		getData()
	}, 200)
})

onMounted(() => {
	showFiltersDrawer.value = false
	setTimeout(() => {
		loadingFilters.value = false
	}, 1000)
})
</script>

<style lang="scss" scoped>
.alerts-list {
	:deep() {
		.n-spin-body {
			top: 100px;
			text-align: center;
			width: 80%;
		}
	}
	.list {
		container-type: inline-size;
		min-height: 200px;

		.alert-summary {
			animation: alert-summary-fade 0.3s forwards;
			opacity: 0;

			@for $i from 0 through 20 {
				&:nth-child(#{$i}) {
					animation-delay: $i * 0.05s;
				}
			}

			@keyframes alert-summary-fade {
				from {
					opacity: 0;
					transform: translateY(10px);
				}
				to {
					opacity: 1;
				}
			}
		}
	}
}
</style>
