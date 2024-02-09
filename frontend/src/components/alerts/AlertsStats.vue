<template>
	<div class="alerts-stats">
		<n-tabs default-value="countByHost" animated type="line" :tabs-padding="24">
			<n-tab-pane name="countByHost" tab="By Host">
				<n-spin :show="loadingCountByHost">
					<template #description>Alerts are being fetched, this may take up to 1 minute.</template>

					<div class="list">
						<template v-if="countByHost.length">
							<AlertsStatsItem
								v-for="summary of countByHost"
								:key="summary.agent_name"
								:summary="summary"
								class="mb-2"
							/>
						</template>
						<template v-else>
							<n-empty
								description="No items found"
								class="justify-center h-48"
								v-if="!loadingCountByHost"
							/>
						</template>
					</div>
				</n-spin>
			</n-tab-pane>
			<n-tab-pane name="countByRule" tab="By Rule">
				<n-spin :show="loadingCountByRule">
					<template #description>Alerts are being fetched, this may take up to 1 minute.</template>

					<div class="list">
						<template v-if="countByRule.length">
							<AlertsStatsItem
								v-for="summary of countByRule"
								:key="summary.rule"
								:summary="summary"
								class="mb-2"
							/>
						</template>
						<template v-else>
							<n-empty
								description="No items found"
								class="justify-center h-48"
								v-if="!loadingCountByRule"
							/>
						</template>
					</div>
				</n-spin>
			</n-tab-pane>
			<n-tab-pane name="countByRuleHost" tab="By Rule & Host">
				<n-spin :show="loadingCountByRuleHost">
					<template #description>Alerts are being fetched, this may take up to 1 minute.</template>

					<div class="list">
						<template v-if="countByRuleHost.length">
							<AlertsStatsItem
								v-for="summary of countByRuleHost"
								:key="summary.agent_name + summary.rule"
								:summary="summary"
								class="mb-2"
							/>
						</template>
						<template v-else>
							<n-empty
								description="No items found"
								class="justify-center h-48"
								v-if="!loadingCountByRuleHost"
							/>
						</template>
					</div>
				</n-spin>
			</n-tab-pane>
		</n-tabs>
	</div>
</template>

<script setup lang="ts">
import { ref, onBeforeMount, toRefs, onBeforeUnmount } from "vue"
import { useMessage, NSpin, NEmpty, NTabs, NTabPane } from "naive-ui"
import Api from "@/api"
import AlertsStatsItem from "./AlertsStatsItem.vue"
import type { AlertsByHost, AlertsByRule, AlertsByRulePerHost } from "@/types/alerts.d"
import type { AlertsSummaryQuery } from "@/api/alerts"
import axios from "axios"
import { onMounted } from "vue"
// import { alerts_by_host, alerts_by_rule, alerts_by_rule_per_host } from "./mock"

const props = withDefaults(defineProps<{ filters?: AlertsSummaryQuery }>(), {
	filters: () => ({})
})
const { filters } = toRefs(props)

export interface AlertsStatsCTX {
	startSearch: () => void
}

const emit = defineEmits<{
	(e: "mounted", value: AlertsStatsCTX): void
}>()

const message = useMessage()
const countByHost = ref<AlertsByHost[]>([])
const countByRule = ref<AlertsByRule[]>([])
const countByRuleHost = ref<AlertsByRulePerHost[]>([])
const loadingCountByHost = ref(false)
const loadingCountByRule = ref(false)
const loadingCountByRuleHost = ref(false)
let abortControllerByHost: AbortController | null = null
let abortControllerByRule: AbortController | null = null
let abortControllerByRuleHost: AbortController | null = null

function getCountByHost() {
	loadingCountByHost.value = true

	abortControllerByHost = new AbortController()

	Api.alerts
		.getCountByHost(filters.value, abortControllerByHost.signal)
		.then(res => {
			if (res.data.success) {
				countByHost.value = res.data?.alerts_by_host || []
			} else {
				message.warning(res.data?.message || "An error occurred. Please try again later.")
			}
		})
		.catch(err => {
			if (!axios.isCancel(err)) {
				countByHost.value = []

				message.error(err.response?.data?.message || "An error occurred. Please try again later.")
			}
		})
		.finally(() => {
			loadingCountByHost.value = false
		})
}

function getCountByRule() {
	loadingCountByRule.value = true

	abortControllerByRule = new AbortController()

	Api.alerts
		.getCountByRule(filters.value, abortControllerByRule.signal)
		.then(res => {
			if (res.data.success) {
				countByRule.value = res.data?.alerts_by_rule || []
			} else {
				message.warning(res.data?.message || "An error occurred. Please try again later.")
			}
		})
		.catch(err => {
			if (!axios.isCancel(err)) {
				countByRule.value = []

				message.error(err.response?.data?.message || "An error occurred. Please try again later.")
			}
		})
		.finally(() => {
			loadingCountByRule.value = false
		})
}

function getCountByRuleHost() {
	loadingCountByRuleHost.value = true

	abortControllerByRuleHost = new AbortController()

	Api.alerts
		.getCountByRuleHost(filters.value, abortControllerByRuleHost.signal)
		.then(res => {
			if (res.data.success) {
				countByRuleHost.value = res.data?.alerts_by_rule_per_host || []
			} else {
				message.warning(res.data?.message || "An error occurred. Please try again later.")
			}
		})
		.catch(err => {
			if (!axios.isCancel(err)) {
				countByRuleHost.value = []

				message.error(err.response?.data?.message || "An error occurred. Please try again later.")
			}
		})
		.finally(() => {
			loadingCountByRuleHost.value = false
		})
}

function startSearch() {
	cancelSearch()

	setTimeout(() => {
		getCountByHost()
		getCountByRule()
		getCountByRuleHost()
	}, 200)
}

function cancelSearch() {
	abortControllerByHost?.abort()
	abortControllerByRule?.abort()
	abortControllerByRuleHost?.abort()
}

onBeforeMount(() => {
	/*
	countByHost.value = alerts_by_host as AlertsByHost[]
	countByRule.value = alerts_by_rule as AlertsByRule[]
	countByRuleHost.value = alerts_by_rule_per_host as AlertsByRulePerHost[]
	*/

	startSearch()
})

onMounted(() => {
	emit("mounted", {
		startSearch
	})
})

onBeforeUnmount(() => {
	cancelSearch()
})
</script>

<style lang="scss" scoped>
.alerts-stats {
	:deep() {
		.n-spin-container {
			min-height: 200px;
		}
		.n-spin-body {
			top: 100px;
			text-align: center;
			width: 80%;
		}
	}
	.list {
		padding: var(--n-body-padding);
	}
}
</style>
