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
							<code>{{ totalAlertsSummary }}</code>
						</div>
						<div class="box">
							Total Alerts:
							<code>{{ totalAlerts }}</code>
						</div>
					</div>
				</n-popover>
			</div>
			<div class="filters flex gap-2">
				<n-form-item label="Filter key/value" size="small">
					<n-input-group>
						<n-select
							v-model:value="alertField"
							:options="alertFieldOptions"
							filterable
							clearable
							tag
							:render-tag="renderFieldTag"
							:render-label="renderFieldLabel"
							placeholder="Alert Field"
							class="!min-w-48"
						>
							<template #action>
								<n-button size="small" @click="clearFieldsHistory()" quaternary class="!w-full">
									<template #icon>
										<Icon :name="ClearIcon"></Icon>
									</template>
									Clear history
								</n-button>
							</template>
							<template #empty>
								<n-empty description="Empty Field history" class="text-center"></n-empty>
							</template>
						</n-select>
						<n-input v-model:value="alertValue" clearable placeholder="Field value" />
					</n-input-group>
				</n-form-item>
				<n-form-item label="Agent" size="small">
					<n-select
						size="small"
						v-model:value="hostname"
						:options="hostnameOptions"
						placeholder="Agents list"
						clearable
						class="!w-36"
					/>
				</n-form-item>
				<n-form-item label="Index" size="small">
					<n-select
						size="small"
						v-model:value="indexname"
						:options="indexnameOptions"
						clearable
						filterable
						placeholder="Indices list"
						class="!w-36"
					/>
				</n-form-item>
				<n-form-item label="Alerts for index" size="small">
					<n-select size="small" v-model:value="maxAlerts" :options="maxAlertsOptions" class="!w-36" />
				</n-form-item>
				<n-form-item label="Time range" size="small">
					<n-select size="small" v-model:value="timerange" :options="timerangeOptions" class="!w-32" />
				</n-form-item>
			</div>
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
import { ref, onBeforeMount, toRefs, watch, type VNodeChild, h, computed } from "vue"
import {
	useMessage,
	NSpin,
	NSelect,
	NPopover,
	NButton,
	NInput,
	NInputGroup,
	NEmpty,
	NFormItem,
	type SelectOption
} from "naive-ui"
import Api from "@/api"
import AlertsSummaryItem, { type AlertsSummaryExt } from "./AlertsSummary.vue"
import { useResizeObserver } from "@vueuse/core"
import Icon from "@/components/common/Icon.vue"
import type { AlertsSummary } from "@/types/alerts.d"
import { useStorage } from "@vueuse/core"
import type { AlertsQueryTimeRange, AlertsSummaryQuery } from "@/api/alerts"
import _uniqBy from "lodash/uniqBy"
import { alerts_summary } from "./mock"
import type { IndexStats } from "@/types/indices.d"
import { nextTick } from "vue"

const props = defineProps<{ agentHostname?: string }>()
const { agentHostname } = toRefs(props)

const message = useMessage()
const loadingIndex = ref(false)
const loading = ref(false)
const indices = ref<IndexStats[] | null>(null)
const alertsSummaryList = ref<AlertsSummaryExt[]>([])
const header = ref()

const InfoIcon = "carbon:information"
const ClearIcon = "mdi:broom"

const totalAlertsSummary = computed<number>(() => {
	return alertsSummaryList.value.length || 0
})
const totalAlerts = computed<number>(() => {
	return alertsSummaryList.value.reduce((acc: number, val: AlertsSummaryExt) => {
		return acc + val.alerts.length
	}, 0)
})

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

const indexnameOptions = computed(() => {
	return (indices.value || []).map(o => ({ value: o.index, label: o.index }))
})
const indexname = ref<string | null>(null)

const alertFieldOptions = useStorage<{ label: string; value: string }[]>("alert-fields-history", [], localStorage)
const alertField = ref<string | null>(null)
const alertValue = ref<string | null>(null)

function clearFieldsHistory(field?: string) {
	if (!field) {
		alertFieldOptions.value = []
	} else {
		alertFieldOptions.value = alertFieldOptions.value.filter(o => o.label !== field)
	}
}

function renderFieldTag({ option }: { option: SelectOption; handleClose: () => void }): VNodeChild {
	return h("div", {}, [option.label as string])
}

function renderFieldLabel(option: SelectOption): VNodeChild {
	if (option.type === "group") return option.label + "(Cool!)"
	return [
		h(Icon, {
			style: {
				verticalAlign: "-0.20em",
				marginRight: "4px",
				opacity: 0.6
			},
			name: `carbon:close`,
			onClick(e: Event) {
				e.stopImmediatePropagation()
				e.stopPropagation()
				clearFieldsHistory(option.label?.toString())
			}
		}),
		option.label?.toString()
	]
}

alertsSummaryList.value = alerts_summary as AlertsSummary[]

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

	const filter: AlertsSummaryQuery = {}

	indexname.value && (filter.indexName = indexname.value)
	hostname.value && (filter.agentHostname = hostname.value)
	maxAlerts.value && (filter.maxAlerts = maxAlerts.value)
	timerange.value && (filter.timerange = timerange.value)
	alertField.value && (filter.alertField = alertField.value)
	alertValue.value && (filter.alertValue = alertValue.value)

	Api.alerts
		.getAll(filter)
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
				indices.value = res.data.indices_stats

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

useResizeObserver(header, entries => {
	const entry = entries[0]
	const { width } = entry.contentRect

	console.log(width)
})

watch(alertField, val => {
	if (val) {
		alertFieldOptions.value = _uniqBy(
			[...JSON.parse(JSON.stringify(alertFieldOptions.value)), { label: val, value: val }],
			o => o.label
		)
	}
})
/*
watch([currentPage, pageSize, timerange], ([page, pageSize, timerange]) => {
	getData(page, pageSize, timerange)
})
*/
onBeforeMount(() => {
	agentHostname?.value && (hostname.value = agentHostname.value)
	//getData()
	getIndices()
})
</script>

<style lang="scss" scoped>
.list {
	container-type: inline-size;
}
</style>
