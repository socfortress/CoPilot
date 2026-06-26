<template>
	<div class="flex flex-col gap-12">
		<MetricsDashboardFilters
			v-model:selected-host="selectedHost"
			v-model:selected-range="selectedRange"
			@refresh="reloadMountedSections"
		/>

		<n-card v-if="!selectedHost" class="p-12 text-center">
			<n-empty description="Select a host to view performance metrics">
				<template #icon>
					<Icon :name="ChartIcon" :size="40" />
				</template>
			</n-empty>
		</n-card>

		<n-tabs v-else type="line" animated>
			<n-tab-pane name="summary" tab="Summary" display-directive="show">
				<MetricsDashboardSummary
					ref="summaryRef"
					:host="selectedHost"
					:range="selectedRange"
					:show-title="false"
				/>
			</n-tab-pane>
			<n-tab-pane name="cpu" tab="CPU" display-directive="show:lazy">
				<MetricsDashboardCpu ref="cpuRef" :host="selectedHost" :range="selectedRange" :show-title="false" />
			</n-tab-pane>
			<n-tab-pane name="memory" tab="Memory" display-directive="show:lazy">
				<MetricsDashboardMemory
					ref="memoryRef"
					:host="selectedHost"
					:range="selectedRange"
					:show-title="false"
				/>
			</n-tab-pane>
			<n-tab-pane name="kernel" tab="Kernel" display-directive="show:lazy">
				<MetricsDashboardKernel
					ref="kernelRef"
					:host="selectedHost"
					:range="selectedRange"
					:show-title="false"
				/>
			</n-tab-pane>
			<n-tab-pane name="disks" tab="Disks" display-directive="show:lazy">
				<MetricsDashboardDisks ref="disksRef" :host="selectedHost" :range="selectedRange" :show-title="false" />
			</n-tab-pane>
			<n-tab-pane name="processes" tab="Processes" display-directive="show:lazy">
				<MetricsDashboardProcesses
					ref="processesRef"
					:host="selectedHost"
					:range="selectedRange"
					:show-title="false"
				/>
			</n-tab-pane>
			<n-tab-pane name="network" tab="Network" display-directive="show:lazy">
				<MetricsDashboardNetwork
					ref="networkRef"
					:host="selectedHost"
					:range="selectedRange"
					:show-title="false"
				/>
			</n-tab-pane>
		</n-tabs>
	</div>
</template>

<script setup lang="ts">
import type { Ref } from "vue"
import type { MetricsDashboardSectionExpose } from "@/types/metrics"
import { NCard, NEmpty, NTabPane, NTabs } from "naive-ui"
import { ref } from "vue"
import Icon from "@/components/common/Icon.vue"
import MetricsDashboardCpu from "./DashboardSections/MetricsDashboardCpu.vue"
import MetricsDashboardDisks from "./DashboardSections/MetricsDashboardDisks.vue"
import MetricsDashboardFilters from "./DashboardSections/MetricsDashboardFilters.vue"
import MetricsDashboardKernel from "./DashboardSections/MetricsDashboardKernel.vue"
import MetricsDashboardMemory from "./DashboardSections/MetricsDashboardMemory.vue"
import MetricsDashboardNetwork from "./DashboardSections/MetricsDashboardNetwork.vue"
import MetricsDashboardProcesses from "./DashboardSections/MetricsDashboardProcesses.vue"
import MetricsDashboardSummary from "./DashboardSections/MetricsDashboardSummary.vue"

const ChartIcon = "carbon:chart-line"

const selectedHost = ref<string | null>(null)
const selectedRange = ref("1")

const summaryRef = ref<MetricsDashboardSectionExpose | null>(null)
const cpuRef = ref<MetricsDashboardSectionExpose | null>(null)
const memoryRef = ref<MetricsDashboardSectionExpose | null>(null)
const kernelRef = ref<MetricsDashboardSectionExpose | null>(null)
const disksRef = ref<MetricsDashboardSectionExpose | null>(null)
const processesRef = ref<MetricsDashboardSectionExpose | null>(null)
const networkRef = ref<MetricsDashboardSectionExpose | null>(null)

const sectionRefs: Array<Ref<MetricsDashboardSectionExpose | null>> = [
	summaryRef,
	cpuRef,
	memoryRef,
	kernelRef,
	disksRef,
	processesRef,
	networkRef
]

function reloadMountedSections() {
	for (const sectionRef of sectionRefs) {
		sectionRef.value?.reload()
	}
}
</script>
