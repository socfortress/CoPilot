<template>
	<n-spin :show="loading">
		<div class="header flex items-center justify-end gap-2" ref="header">
			<div class="info grow flex gap-5">
				<n-popover overlap placement="bottom-start">
					<template #trigger>
						<div class="bg-color border-radius">
							<n-button size="small">
								<template #icon>
									<Icon :name="InfoIcon"></Icon>
								</template>
							</n-button>
						</div>
					</template>
					<div class="flex flex-col gap-2">
						<div class="box">
							Total Items:
							<code>{{ total }}</code>
						</div>
						<div class="box">
							Total Alerts:
							<code>{{ total }}</code>
						</div>
					</div>
				</n-popover>
			</div>

			<n-select size="small" v-model:value="maxAlerts" :options="maxAlertsOptions" class="!w-32" />
			<n-select size="small" v-model:value="timerange" :options="timerangeOptions" class="!w-32" />
			<n-select size="small" v-model:value="hostname" :options="hostnameOptions" class="!w-32" />
			<n-select size="small" v-model:value="indexname" :options="indexnameOptions" class="!w-32" />
		</div>
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
</template>

<script setup lang="ts">
import { ref, onBeforeMount, toRefs } from "vue"
import { useMessage, NSpin, NSelect, NPopover, NButton, NEmpty } from "naive-ui"
import Api from "@/api"
import AlertsSummaryItem from "./AlertsSummary.vue"
import { useResizeObserver } from "@vueuse/core"
import Icon from "@/components/common/Icon.vue"
import type { AlertsSummary } from "@/types/alerts.d"
import type { AlertsQueryTimeRange, AlertsSummaryQuery } from "@/api/alerts"

const props = defineProps<{ agentHostname?: string }>()
const { agentHostname } = toRefs(props)

// TODO: add key/value filter (alert_field/alert_value)

const message = useMessage()
const loading = ref(false)
const alertsSummaryList = ref<AlertsSummary[]>([])
const total = ref(0)
const header = ref()

const InfoIcon = "carbon:information"

const timerangeOptions: { label: string; value: AlertsQueryTimeRange }[] = [
	{ label: "1 Hour", value: "1h" },
	{ label: "6 Hours", value: "6h" },
	{ label: "12 Hours", value: "12h" },
	{ label: "1 Day", value: "1d" },
	{ label: "2 Day", value: "2d" },
	{ label: "5 Day", value: "5d" },
	{ label: "1 Week", value: "1w" },
	{ label: "2 Week", value: "2w" },
	{ label: "3 Week", value: "3w" },
	{ label: "4 Week", value: "4w" }
]
const timerange = ref<AlertsQueryTimeRange>(timerangeOptions[2].value)

const maxAlertsOptions = [
	{ label: "1 Alert", value: 1 },
	{ label: "5 Alert", value: 5 },
	{ label: "10 Alert", value: 10 },
	{ label: "20 Alert", value: 20 }
]
const maxAlerts = ref<number>(maxAlertsOptions[1].value)

const hostnameOptions = ref<{ label: string; value: string }[]>([])
const hostname = ref<string | null>(null)

const indexnameOptions = ref<{ label: string; value: string }[]>([])
const indexname = ref<string | null>(null)

function getData() {
	loading.value = true

	const filter: AlertsSummaryQuery = {}

	indexname.value && (filter.indexName = indexname.value)
	hostname.value && (filter.agentHostname = hostname.value)
	maxAlerts.value && (filter.maxAlerts = maxAlerts.value)
	timerange.value && (filter.timerange = timerange.value)

	Api.alerts
		.getAll()
		.then(res => {
			if (res.data.success) {
				alertsSummaryList.value = res.data?.alerts_summary || []
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
	agentHostname?.value && (hostname.value = agentHostname.value)
	getData()
})
</script>

<style lang="scss" scoped>
.list {
	container-type: inline-size;
}
</style>
