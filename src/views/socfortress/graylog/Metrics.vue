<template>
	<div class="page">
		<div class="info mb-7">
			Graylog metrics detail the current load or backlog of logs being processed by the Graylog server. Also in
			this payload is the
			<code>uncommitted_journal_entries</code>
			. If this value is greater than
			<code>50,000</code>
			I'd like for that to be
			<strong>highlighted</strong>
			on the page as an issue.
		</div>

		<div class="debug">
			<pre>lastCheck: {{ lastCheck }}</pre>
		</div>

		<div class="debug">
			<pre>uncommittedJournalEntries: {{ uncommittedJournalEntries }}</pre>
		</div>

		<div class="metrics-list">
			<n-card
				v-for="group of throughputMetrics"
				:key="group.groupName"
				:title="group.groupName"
				size="small"
				segmented
				class="metrics-group"
				content-style="padding:0"
			>
				<div class="list">
					<div
						v-for="metric of group.throughputMetrics"
						:key="metric.metric"
						class="flex items-center gap-4 metric-wrap"
					>
						<div class="metric basis-2/3">
							{{ metric.metric }}
						</div>
						<div class="value basis-1/3">
							<n-progress type="line" status="success" :percentage="metric.percentage">
								{{ metric.value }}
							</n-progress>
						</div>
					</div>
				</div>
			</n-card>
		</div>
	</div>
</template>

<script setup lang="ts">
import { ref, onBeforeMount } from "vue"
import { useMessage, NCard, NProgress } from "naive-ui"
import Api from "@/api"
import type { ThroughputMetric } from "@/types/graylog/index.d"
import _groupBy from "lodash/groupBy"
import _map from "lodash/map"
import _trim from "lodash/trim"
import { onBeforeUnmount } from "vue"

interface Metrics {
	groupName: string
	throughputMetrics: (ThroughputMetric & { name: string; percentage: number })[]
}

const message = useMessage()
const loading = ref(false)
const uncommittedJournalEntries = ref(0)
const throughputMetrics = ref<Metrics[]>([])
const lastCheck = ref<null | Date>(null)
const getDataTimer = ref<NodeJS.Timeout | null>(null)

function sanitizeMetrics(metrics: ThroughputMetric[]): Metrics[] {
	const keywords = ["input", "output", "process"]

	const tempData = metrics.map(o => {
		const obj = { ...o } as ThroughputMetric & { name: string; percentage: number }
		obj.name = obj.metric
		for (const key of keywords) {
			obj.name = _trim(obj.name.replace(key, "").replace("..", "."), ".")
		}
		return obj
	})

	const groups = _groupBy(tempData, "name")

	return _map(groups, group => {
		const max = Math.max(...group.map(g => g.value)) || 1

		for (const m of group) {
			m.percentage = (m.value / max) * 100
		}

		const groupObj: Metrics = {
			groupName: group[0].name,
			throughputMetrics: group
		}
		return groupObj
	})
}

function getData() {
	loading.value = true

	Api.graylog
		.getMetrics()
		.then(res => {
			if (res.data.success) {
				throughputMetrics.value = sanitizeMetrics(res.data.throughput_metrics || [])
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

onBeforeMount(() => {
	getData()
	getDataTimer.value = setInterval(getData, 5000)
})

onBeforeUnmount(() => {
	if (getDataTimer.value !== null) {
		clearInterval(getDataTimer.value)
	}
})
</script>

<style lang="scss" scoped>
.page {
	.metrics-list {
		.metrics-group {
			@apply mb-6;

			.list {
				background-color: var(--bg-secondary-color);
				.metric-wrap {
					@apply py-3 px-4;
					.metric {
						line-height: 1.1;
					}
					.value {
					}

					&:not(:last-child) {
						border-bottom: var(--border-small-100);
					}
				}
			}
		}
	}
}
</style>
