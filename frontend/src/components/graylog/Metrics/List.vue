<template>
	<div class="flex flex-col">
		<n-card
			v-for="group of sanitizedMetrics"
			:key="group.groupName"
			:title="group.groupName"
			size="small"
			segmented
			class="mb-6 overflow-hidden last:mb-0"
			content-class="p-0!"
		>
			<div class="bg-secondary divide-border divide-y">
				<div
					v-for="metric of group.throughputMetrics"
					:key="metric.metric"
					class="flex items-center gap-4 px-4 py-3"
				>
					<div class="basis-2/3 leading-tight">
						{{ metric.metric }}
					</div>
					<div class="basis-1/3">
						<n-progress type="line" status="success" :percentage="metric.percentage">
							<span class="font-mono">
								{{ metric.value }}
							</span>
						</n-progress>
					</div>
				</div>
			</div>
		</n-card>
	</div>
</template>

<script setup lang="ts">
import type { ThroughputMetric } from "@/types/graylog/metrics"
import _groupBy from "lodash/groupBy"
import _map from "lodash/map"
import _trim from "lodash/trim"
import { NCard, NProgress } from "naive-ui"
import { computed, toRefs } from "vue"

interface Metrics {
	groupName: string
	throughputMetrics: (ThroughputMetric & { name: string; percentage: number })[]
}

const props = defineProps<{
	throughputMetrics: ThroughputMetric[]
}>()
const { throughputMetrics } = toRefs(props)

const sanitizedMetrics = computed<Metrics[]>(() => {
	return sanitizeMetrics(throughputMetrics.value)
})

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
			groupName: group[0]?.name ?? "",
			throughputMetrics: group
		}
		return groupObj
	})
}
</script>
