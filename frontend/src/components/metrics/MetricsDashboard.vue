<template>
	<div class="flex flex-col gap-12">
		<MetricsDashboardFilters
			v-model:selected-host="selectedHost"
			v-model:selected-range="selectedRange"
			:host-options
			:hosts-loading
			:loading
			@refresh="refresh"
		/>

		<!-- Empty state -->
		<n-card v-if="!selectedHost" class="p-12 text-center">
			<n-empty description="Select a host to view performance metrics">
				<template #icon>
					<Icon :name="ChartIcon" :size="40" />
				</template>
			</n-empty>
		</n-card>

		<!-- Loading -->
		<n-spin v-else-if="loading && !loaded" class="flex min-h-80 items-center justify-center" show />

		<!-- Dashboard -->
		<div v-else-if="loaded" class="flex flex-col gap-8">
			<MetricsDashboardSummary :summary />

			<MetricsDashboardCpu :cpu />

			<MetricsDashboardMemory :memory />

			<MetricsDashboardKernel :kernel />

			<MetricsDashboardDisks :disks />

			<MetricsDashboardProcesses :processes />

			<MetricsDashboardNetwork :network />
		</div>
	</div>
</template>

<script setup lang="ts">
import type { ApiError } from "@/types/common.d"
import type {
	MetricsCpuData,
	MetricsDisksData,
	MetricsKernelData,
	MetricsMemoryData,
	MetricsNetworkData,
	MetricsProcessesData,
	MetricsSummaryData
} from "@/types/metrics.d"
import { NCard, NEmpty, NSpin, useMessage } from "naive-ui"
import { computed, onBeforeMount, ref } from "vue"
import Api from "@/api"
import Icon from "@/components/common/Icon.vue"
import { getApiErrorMessage } from "@/utils"
import MetricsDashboardCpu from "./DashboardSections/MetricsDashboardCpu.vue"
import MetricsDashboardDisks from "./DashboardSections/MetricsDashboardDisks.vue"
import MetricsDashboardFilters from "./DashboardSections/MetricsDashboardFilters.vue"
import MetricsDashboardKernel from "./DashboardSections/MetricsDashboardKernel.vue"
import MetricsDashboardMemory from "./DashboardSections/MetricsDashboardMemory.vue"
import MetricsDashboardNetwork from "./DashboardSections/MetricsDashboardNetwork.vue"
import MetricsDashboardProcesses from "./DashboardSections/MetricsDashboardProcesses.vue"
import MetricsDashboardSummary from "./DashboardSections/MetricsDashboardSummary.vue"

const ChartIcon = "carbon:chart-line"

const message = useMessage()
const loading = ref(false)
const loaded = ref(false)
const hostsLoading = ref(false)
const hosts = ref<string[]>([])
const selectedHost = ref<string | null>(null)
const selectedRange = ref("1")

const summary = ref<MetricsSummaryData>({})
const cpu = ref<MetricsCpuData>({})
const memory = ref<MetricsMemoryData>({})
const kernel = ref<MetricsKernelData>({})
const disks = ref<MetricsDisksData>({})
const processes = ref<MetricsProcessesData>({})
const network = ref<MetricsNetworkData>({})

const hostOptions = computed(() => hosts.value.map(h => ({ label: h, value: h })))

async function loadHosts() {
	hostsLoading.value = true
	try {
		const res = await Api.metrics.getHosts()
		if (res.data.success) {
			hosts.value = res.data.hosts || []
		} else {
			message.warning(res.data?.message || "Failed to load hosts")
		}
	} catch (err: unknown) {
		message.error(getApiErrorMessage(err as ApiError) || "Failed to load hosts")
	} finally {
		hostsLoading.value = false
	}
}

async function refresh() {
	if (!selectedHost.value) return
	loading.value = true

	const host = selectedHost.value
	const range = selectedRange.value

	try {
		const [sumRes, cpuRes, memRes, kerRes, dskRes, prcRes, netRes] = await Promise.all([
			Api.metrics.getSummary(host, range),
			Api.metrics.getCpu(host, range),
			Api.metrics.getMemory(host, range),
			Api.metrics.getKernel(host, range),
			Api.metrics.getDisks(host, range),
			Api.metrics.getProcesses(host, range),
			Api.metrics.getNetwork(host, range)
		])

		for (const res of [sumRes, cpuRes, memRes, kerRes, dskRes, prcRes, netRes]) {
			if (!res.data.success) {
				message.warning(res.data?.message || "Error fetching metrics")
				loading.value = false
				return
			}
		}

		summary.value = sumRes.data.data || {}
		cpu.value = cpuRes.data.data || {}
		memory.value = memRes.data.data || {}
		kernel.value = kerRes.data.data || {}
		disks.value = dskRes.data.data || {}
		processes.value = prcRes.data.data || {}
		network.value = netRes.data.data || {}

		loaded.value = true
	} catch (err: unknown) {
		message.error(getApiErrorMessage(err as ApiError) || "Error fetching metrics")
	} finally {
		loading.value = false
	}
}

onBeforeMount(() => {
	loadHosts()
})
</script>
