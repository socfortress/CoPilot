<template>
	<div class="flex flex-wrap items-center justify-start gap-3">
		<n-input-group class="w-auto!">
			<n-input-group-label size="small" class="flex items-center gap-2">
				<Icon :name="HostIcon" :size="14" />
				Host
			</n-input-group-label>
			<n-select
				v-model:value="selectedHost"
				:options="hostOptions"
				:loading="hostsLoading"
				placeholder="Select host"
				size="small"
				filterable
				class="w-52!"
				:consistent-menu-width="false"
			/>
		</n-input-group>

		<n-input-group class="w-auto!">
			<n-input-group-label size="small" class="flex items-center gap-2">
				<Icon :name="TimeRangeIcon" :size="14" />
				Time Range
			</n-input-group-label>
			<n-select
				v-model:value="selectedRange"
				:options="rangeOptions"
				size="small"
				class="w-44!"
				:consistent-menu-width="false"
			/>
		</n-input-group>

		<n-button size="small" type="primary" secondary :disabled="!selectedHost" @click="emit('refresh')">
			<template #icon>
				<Icon :name="RefreshIcon" :size="14" />
			</template>
			Refresh
		</n-button>
	</div>
</template>

<script setup lang="ts">
import type { ApiError } from "@/types/common.d"
import { NButton, NInputGroup, NInputGroupLabel, NSelect, useMessage } from "naive-ui"
import { computed, onBeforeMount, ref } from "vue"
import Api from "@/api"
import Icon from "@/components/common/Icon.vue"
import { getApiErrorMessage } from "@/utils"

const emit = defineEmits<{
	refresh: []
}>()

const selectedHost = defineModel<string | null>("selectedHost")
const selectedRange = defineModel<string>("selectedRange", { default: "1" })

const message = useMessage()
const hostsLoading = ref(false)
const hosts = ref<string[]>([])

const hostOptions = computed(() => hosts.value.map(host => ({ label: host, value: host })))

const HostIcon = "carbon:bare-metal-server"
const TimeRangeIcon = "carbon:time"
const RefreshIcon = "carbon:renew"

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
			message.warning(res.data.message || "Failed to load hosts")
		}
	} catch (err: unknown) {
		message.error(getApiErrorMessage(err as ApiError) || "Failed to load hosts")
	} finally {
		hostsLoading.value = false
	}
}

onBeforeMount(() => {
	loadHosts()
})
</script>
