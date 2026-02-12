<template>
	<div class="page">
		<div class="header flex flex-wrap items-center justify-between gap-4">
			<div class="info flex items-center gap-3">
				<n-button size="small" type="primary" secondary :loading="loading" @click="getData()">
					<template #icon>
						<Icon :name="UpdatedIcon" :size="15" />
					</template>
				</n-button>
				<span>Last check:</span>
				<strong>{{ lastCheck ? formatDate(lastCheck, dFormats.datetimesec) : "..." }}</strong>
			</div>

			<div class="toolbar flex items-center gap-3">
				<n-button v-if="!isRunning" size="small" type="primary" class="w-24!" @click="start()">
					<template #icon>
						<Icon :name="StartIcon" />
					</template>
					Start
				</n-button>
				<n-button v-if="isRunning" size="small" type="error" ghost class="w-24!" @click="stop()">
					<template #icon>
						<Icon :name="StopIcon" />
					</template>
					Stop
				</n-button>
				<n-select v-model:value="intervalSelected" size="small" :options="intervalOptions" class="w-36!" />
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
import type { ThroughputMetric } from "@/types/graylog/metrics.d"
import { useStorage } from "@vueuse/core"
import { NButton, NSelect, useMessage } from "naive-ui"
import { computed, nextTick, onBeforeMount, onBeforeUnmount, ref, watch } from "vue"
import Api from "@/api"
import Icon from "@/components/common/Icon.vue"
import MetricsList from "@/components/graylog/Metrics/List.vue"
import UncommittedEntries from "@/components/graylog/Metrics/UncommittedEntries.vue"
import { useSettingsStore } from "@/stores/settings"
import { formatDate } from "@/utils/format"

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
