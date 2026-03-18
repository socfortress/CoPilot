<template>
	<div class="metrics-dashboard">
		<!-- Filters -->
		<div class="header mb-6 flex flex-wrap items-end gap-4">
			<div>
				<label class="mb-1 block text-xs" :style="{ color: 'var(--fg-secondary-color)' }">Host</label>
				<n-select
					v-model:value="selectedHost"
					:options="hostOptions"
					:loading="hostsLoading"
					placeholder="Select host"
					class="w-52!"
					size="small"
					@update:value="refresh"
				/>
			</div>
			<div>
				<label class="mb-1 block text-xs" :style="{ color: 'var(--fg-secondary-color)' }">Time Range</label>
				<n-select
					v-model:value="selectedRange"
					:options="rangeOptions"
					class="w-44!"
					size="small"
					@update:value="refresh"
				/>
			</div>
			<n-button size="small" type="primary" secondary :loading :disabled="!selectedHost" @click="refresh">
				<template #icon>
					<Icon :name="RefreshIcon" :size="15" />
				</template>
			</n-button>
		</div>

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
		<div v-else-if="loaded">
			<!-- Summary Section -->
			<section class="mb-8">
				<h3 class="mb-4 text-lg font-semibold" :style="{ color: 'var(--primary-color)' }">Metrics Summary</h3>
				<div class="mb-4 grid grid-cols-2 gap-4 md:grid-cols-4 lg:grid-cols-7">
					<MetricsStatCard label="Uptime" :value="summary.uptime" format="uptime" />
					<MetricsStatCard label="Total Memory" :value="summary.total_mem" format="bytes" />
					<MetricsStatCard label="CPUs" :value="summary.cpus" />
					<MetricsStatCard label="Processes" :value="summary.total_processes" />
					<MetricsStatCard
						label="CPU Idle"
						:value="summary.cpu_idle"
						format="percent"
						:decimals="1"
						:color-thresholds="{ low: 20, mid: 50 }"
					/>
					<MetricsStatCard label="Swap Free" :value="summary.swap_free" format="bytes" />
					<MetricsStatCard label="Users Logged In" :value="summary.logged_on_users" />
				</div>
				<div class="grid grid-cols-1 gap-4 lg:grid-cols-3">
					<n-card>
						<MetricsGauge :value="summary.cpu_idle ?? 0" title="CPU Idle" :height="220" />
					</n-card>
					<n-card class="lg:col-span-2">
						<MetricsChart title="System Load" :series="summary.load || {}" :height="220" />
					</n-card>
				</div>
			</section>

			<!-- CPU Section -->
			<section class="mb-8">
				<h3 class="mb-4 text-lg font-semibold" :style="{ color: 'var(--primary-color)' }">CPU</h3>
				<div class="grid grid-cols-1 gap-4 lg:grid-cols-2">
					<n-card>
						<MetricsChart title="CPU System %" :series="cpu.cpu_usage_system || {}" y-axis-name="%" />
					</n-card>
					<n-card>
						<MetricsChart title="CPU User %" :series="cpu.cpu_usage_user || {}" y-axis-name="%" />
					</n-card>
					<n-card>
						<MetricsChart title="I/O Wait %" :series="cpu.cpu_iowait || {}" y-axis-name="%" />
					</n-card>
					<n-card>
						<MetricsChart title="Soft IRQ %" :series="cpu.cpu_softirq || {}" y-axis-name="%" />
					</n-card>
				</div>
			</section>

			<!-- Memory Section -->
			<section class="mb-8">
				<h3 class="mb-4 text-lg font-semibold" :style="{ color: 'var(--primary-color)' }">Memory</h3>
				<div class="mb-4 grid grid-cols-2 gap-4">
					<MetricsStatCard label="Swap Total" :value="memory.swap_total" format="bytes" />
					<MetricsStatCard label="Swap Free" :value="memory.swap_free" format="bytes" />
				</div>
				<n-card>
					<MetricsChart
						title="Memory Usage"
						:series="memory.mem_used || {}"
						:height="280"
						y-axis-name="bytes"
						format-bytes
					/>
				</n-card>
			</section>

			<!-- Kernel Section -->
			<section class="mb-8">
				<h3 class="mb-4 text-lg font-semibold" :style="{ color: 'var(--primary-color)' }">Kernel</h3>
				<div class="grid grid-cols-1 gap-4 lg:grid-cols-2">
					<n-card>
						<MetricsChart title="Interrupts/sec" :series="kernel.interrupts || {}" y-axis-name="/s" />
					</n-card>
					<n-card>
						<MetricsChart
							title="Processes Forked/sec"
							:series="kernel.processes_forked || {}"
							y-axis-name="/s"
						/>
					</n-card>
				</div>
			</section>

			<!-- Disks Section -->
			<section class="mb-8">
				<h3 class="mb-4 text-lg font-semibold" :style="{ color: 'var(--primary-color)' }">Disks</h3>
				<div class="mb-4">
					<MetricsStatCard label="Total Disk Size" :value="disks.disk_total" format="bytes" />
				</div>
				<div class="grid grid-cols-1 gap-4 lg:grid-cols-2">
					<n-card>
						<MetricsChart title="Disk Usage %" :series="disks.disk_usage || {}" y-axis-name="%" />
					</n-card>
					<n-card>
						<MetricsChart
							title="Disk I/O (bytes/s)"
							:series="disks.disk_io || {}"
							y-axis-name="B/s"
							format-bytes
						/>
					</n-card>
				</div>
			</section>

			<!-- Processes Section -->
			<section class="mb-8">
				<h3 class="mb-4 text-lg font-semibold" :style="{ color: 'var(--primary-color)' }">Processes</h3>
				<div class="mb-4 grid grid-cols-2 gap-4 md:grid-cols-4">
					<MetricsStatCard label="Running" :value="processes.running" />
					<MetricsStatCard label="Sleeping" :value="processes.sleeping" />
					<MetricsStatCard label="Unknown" :value="processes.unknown" />
					<MetricsStatCard label="Zombies" :value="processes.zombies" />
				</div>
				<n-card>
					<MetricsChart title="Process Status" :series="processes.status || {}" :height="280" />
				</n-card>
			</section>

			<!-- Network Section -->
			<section class="mb-8">
				<h3 class="mb-4 text-lg font-semibold" :style="{ color: 'var(--primary-color)' }">Network</h3>
				<div class="mb-4">
					<MetricsStatCard label="TCP Sessions Established" :value="network.tcp_established" />
				</div>
				<div class="grid grid-cols-1 gap-4 lg:grid-cols-2">
					<n-card>
						<MetricsChart
							title="Network Traffic (bytes/s)"
							:series="network.traffic || {}"
							:height="280"
							y-axis-name="B/s"
							format-bytes
						/>
					</n-card>
					<n-card>
						<MetricsChart title="Interface Errors" :series="network.interface_errors || {}" :height="280" />
					</n-card>
				</div>
			</section>
		</div>
	</div>
</template>

<script setup lang="ts">
import { NButton, NCard, NEmpty, NSelect, NSpin, useMessage } from "naive-ui"
import { computed, onBeforeMount, ref } from "vue"
import Api from "@/api"
import Icon from "@/components/common/Icon.vue"
import MetricsChart from "./MetricsChart.vue"
import MetricsGauge from "./MetricsGauge.vue"
import MetricsStatCard from "./MetricsStatCard.vue"

const RefreshIcon = "carbon:update-now"
const ChartIcon = "carbon:chart-line"

const message = useMessage()
const loading = ref(false)
const loaded = ref(false)
const hostsLoading = ref(false)
const hosts = ref<string[]>([])
const selectedHost = ref<string | null>(null)
const selectedRange = ref("1")

const summary = ref<Record<string, any>>({})
const cpu = ref<Record<string, any>>({})
const memory = ref<Record<string, any>>({})
const kernel = ref<Record<string, any>>({})
const disks = ref<Record<string, any>>({})
const processes = ref<Record<string, any>>({})
const network = ref<Record<string, any>>({})

const hostOptions = computed(() => hosts.value.map(h => ({ label: h, value: h })))

const rangeOptions = [
	{ label: "Last 1 Hour", value: "1" },
	{ label: "Last 3 Hours", value: "3" },
	{ label: "Last 6 Hours", value: "6" },
	{ label: "Last 12 Hours", value: "12" },
	{ label: "Last 24 Hours", value: "24" },
	{ label: "Last 2 Days", value: "48" },
	{ label: "Last 7 Days", value: "168" }
]

async function loadHosts() {
	hostsLoading.value = true
	try {
		const res = await Api.metrics.getHosts()
		if (res.data.success) {
			hosts.value = res.data.hosts || []
		} else {
			message.warning(res.data?.message || "Failed to load hosts")
		}
	} catch (err: any) {
		message.error(err.response?.data?.message || "Failed to load hosts")
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
	} catch (err: any) {
		message.error(err.response?.data?.message || "Error fetching metrics")
	} finally {
		loading.value = false
	}
}

onBeforeMount(() => {
	loadHosts()
})
</script>
