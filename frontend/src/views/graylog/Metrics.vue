<template>
	<div class="page">
		<div class="header flex flex-wrap justify-between items-center gap-4">
			<div class="info flex items-center gap-3">
				<n-button size="small" @click="getData()" type="primary" secondary :loading="loading">
					<template #icon><Icon :name="UpdatedIcon" :size="15"></Icon></template>
				</n-button>
				<span>Last check:</span>
				<strong>{{ lastCheck ? formatDate(lastCheck, dFormats.datetimesec) : "..." }}</strong>
			</div>

			<div class="toolbar flex items-center gap-3">
				<n-button size="small" @click="start()" v-if="!isRunning" type="primary" class="!w-24">
					<template #icon><Icon :name="StartIcon"></Icon></template>
					Start
				</n-button>
				<n-button size="small" @click="stop()" v-if="isRunning" type="error" ghost class="!w-24">
					<template #icon><Icon :name="StopIcon"></Icon></template>
					Stop
				</n-button>
				<n-select size="small" v-model:value="intervalSelected" :options="intervalOptions" class="!w-36" />
			</div>
		</div>

		<div class="my-6">
			<UncommittedEntries :value="uncommittedJournalEntries" />
		</div>

		<div>
			<MetricsList :throughput-metrics="throughputMetrics" />
		</div>
	</div>
</template>

<script setup lang="ts">
import { ref, onBeforeMount, computed, watch, nextTick, onBeforeUnmount } from "vue"
import { useMessage, NButton, NSelect } from "naive-ui"
import Api from "@/api"
import type { ThroughputMetric } from "@/types/graylog/index.d"
import Icon from "@/components/common/Icon.vue"
import UncommittedEntries from "@/components/graylog/Metrics/UncommittedEntries.vue"
import MetricsList from "@/components/graylog/Metrics/List.vue"
import { formatDate } from "@/utils"
import { useSettingsStore } from "@/stores/settings"
import { useStorage } from "@vueuse/core"

const UpdatedIcon = "carbon:update-now"
const StopIcon = "carbon:stop"
const StartIcon = "carbon:play"

const message = useMessage()
const loading = ref(false)
const uncommittedJournalEntries = ref(0)
const throughputMetrics = ref<ThroughputMetric[]>([])
const lastCheck = ref<null | Date>(null)
const getDataTimer = ref<NodeJS.Timeout | null>(null)
const dFormats = useSettingsStore().dateFormat
const intervalOptions = [
	{
		label: "1 Second",
		value: 1000
	},
	{
		label: "5 Seconds",
		value: 5000
	},
	{
		label: "10 Seconds",
		value: 10000
	},
	{
		label: "30 Seconds",
		value: 30000
	},
	{
		label: "1 Minute",
		value: 60000
	}
]
const intervalSelected = useStorage<number>("metrics-interval", 5000, localStorage)

const isRunning = computed<boolean>(() => {
	return !!getDataTimer.value
})

function getData() {
	loading.value = true

	Api.graylog
		.getMetrics()
		.then(res => {
			if (res.data.success) {
				throughputMetrics.value = res.data.throughput_metrics || []
				uncommittedJournalEntries.value = res.data.uncommitted_journal_entries || 0
				lastCheck.value = new Date()
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

function stop() {
	if (getDataTimer.value !== null) {
		clearInterval(getDataTimer.value)
		getDataTimer.value = null
	}
}

function start() {
	getDataTimer.value = setInterval(getData, intervalSelected.value)
}

watch(intervalSelected, () => {
	stop()
	nextTick(() => {
		start()
	})
})

onBeforeMount(() => {
	getData()
	start()
})

onBeforeUnmount(() => {
	stop()
})
</script>
