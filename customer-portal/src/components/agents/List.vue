<template>
	<div class="flex flex-col gap-6">
		<Filters v-model:value="filters" :status="statusesList" :os="osList" />

		<div class="flex flex-col gap-2">
			<div ref="headerRef" class="flex items-center justify-between">
				<Chip size="small" :value="loading ? 'Loading...' : paginatedTotal" label="items" />

				<div class="flex items-center gap-2 whitespace-nowrap">
					<n-pagination
						v-model:page="pagination.page"
						v-model:page-size="pagination.pageSize"
						:page-slot
						:show-size-picker
						:page-sizes
						:item-count="paginatedTotal"
						:simple="simpleMode"
						size="small"
					/>
				</div>
			</div>

			<div class="grow overflow-hidden">
				<n-data-table
					bordered
					:loading
					size="small"
					:data="dataPaginated"
					:columns
					:scroll-x="1400"
					class="[&_.n-data-table-th\_\_title]:whitespace-nowrap"
				>
					<template #empty>
						<n-empty description="No agents found">
							<template #extra>try changing the filters</template>
						</n-empty>
					</template>
				</n-data-table>
			</div>

			<div class="flex justify-end">
				<n-pagination
					v-if="paginatedTotal > pagination.pageSize"
					v-model:page="pagination.page"
					:page-size="pagination.pageSize"
					:item-count="paginatedTotal"
					:page-slot="6"
					size="small"
					:simple="simpleMode"
				/>
			</div>
		</div>
	</div>
</template>

<script setup lang="tsx">
import type { DataTableColumns } from "naive-ui"
import type { AgentCriticalUpdateSuccessPayload } from "./AgentCriticalSelect.vue"
import type { AgentsFilters } from "@/components/agents/Filters.vue"
import type { Agent } from "@/types/agents"
import type { ApiError } from "@/types/common"
import { useDebounceFn, useElementSize } from "@vueuse/core"
import axios from "axios"
import { NDataTable, NEmpty, NPagination, NTag, useMessage } from "naive-ui"
import { computed, onBeforeMount, ref, useTemplateRef, watch } from "vue"
import Api from "@/api"
import Filters from "@/components/agents/Filters.vue"
import Chip from "@/components/common/Chip.vue"
import Icon from "@/components/common/Icon.vue"
import { useSettingsStore } from "@/stores/settings"
import { getApiErrorMessage, getStatusColor } from "@/utils"
import { formatDate } from "@/utils/format"
import AgentCriticalSelect from "./AgentCriticalSelect.vue"
import AgentDetailsButton from "./AgentDetailsButton.vue"

const emit = defineEmits<{
	(e: "loaded", value: Agent[]): void
	(e: "loading", value: boolean): void
}>()

const message = useMessage()
const loading = ref(false)
const dFormats = useSettingsStore().dateFormat

const { width: headerWidthRef } = useElementSize(useTemplateRef("headerRef"))
const pageSizes = [10, 25, 50, 100]
const pageSlot = computed(() => (headerWidthRef.value < 800 ? 5 : 8))
const simpleMode = computed(() => headerWidthRef.value < 600)
const showSizePicker = ref(true)

const pagination = ref({
	page: 1,
	pageSize: pageSizes[1]
})

const filters = ref<AgentsFilters>({
	status: null,
	os: null,
	critical: false,
	search: null
})

const data = ref<Agent[]>([])

const dataFiltered = computed(() => {
	return data.value.filter(agent => {
		if (filters.value.status && agent.wazuh_agent_status !== filters.value.status) {
			return false
		}
		if (filters.value.critical && agent.critical_asset !== filters.value.critical) {
			return false
		}
		if (filters.value.os && agent.os !== filters.value.os) {
			return false
		}
		if (
			filters.value.search &&
			!agent.hostname.toLowerCase().includes(filters.value.search.toLowerCase()) &&
			!agent.ip_address.toLowerCase().includes(filters.value.search.toLowerCase()) &&
			!agent.agent_id.toLowerCase().includes(filters.value.search.toLowerCase())
		) {
			return false
		}
		return true
	})
})

const dataPaginated = computed(() => {
	const from = (pagination.value.page - 1) * pagination.value.pageSize
	const to = pagination.value.page * pagination.value.pageSize

	return dataFiltered.value.slice(from, to)
})

const paginatedTotal = computed(() => dataFiltered.value.length)

const statusesList = computed(() => [...new Set(data.value.map(agent => agent.wazuh_agent_status))])
const osList = computed(() => [...new Set(data.value.map(agent => agent.os))])

const columns = computed<DataTableColumns<Agent>>(() => [
	{
		title: "Agent",
		key: "agent_id",
		fixed: simpleMode.value ? undefined : "left",
		width: 280,
		render: row => (
			<div class="flex items-center gap-2">
				<NTag
					type={getStatusColor(row.wazuh_agent_status)}
					round
					class="p-1! [&_.n-tag\_\_icon]:m-0!"
					v-slots={{
						icon: () => <Icon name="carbon:circle-solid" />
					}}
				/>
				<div class="flex flex-col gap-0.5">
					<div class="font-medium">{row.hostname}</div>
					<div class="text-secondary text-xs">
						ID:
						{row.agent_id}
					</div>
				</div>
			</div>
		)
	},
	{
		title: "IP Address",
		key: "ip_address",
		width: 160,
		render: row => <div class="font-mono">{row.ip_address}</div>
	},
	{
		title: "Operating System",
		key: "os",
		render: row => <div>{row.os}</div>
	},
	{
		title: "Last Seen",
		key: "wazuh_last_seen",
		width: 180,
		render: row => <div class="font-mono">{formatDate(row.wazuh_last_seen, dFormats.datetime)}</div>
	},
	{
		title: "Status",
		key: "wazuh_agent_status",
		width: 180,
		render: row => {
			return (
				<div class="flex items-center gap-2">
					<Chip type={getStatusColor(row.wazuh_agent_status)} value={row.wazuh_agent_status.toUpperCase()} />
				</div>
			)
		}
	},
	{
		title: "Critical Asset",
		key: "critical_asset",
		width: 200,
		render: row => {
			return (
				<AgentCriticalSelect
					agentId={row.agent_id}
					critical={row.critical_asset}
					onSuccess={handleCriticalAssetUpdated}
				/>
			)
		}
	},
	{
		title: "Actions",
		key: "actions",
		width: 194,
		render: row => {
			return <AgentDetailsButton agentId={row.agent_id} onCriticalAssetUpdated={handleCriticalAssetUpdated} />
		}
	}
])

let abortController = new AbortController()

const loadAgents = useDebounceFn(async () => {
	loading.value = true

	abortController?.abort()
	abortController = new AbortController()

	try {
		const response = await Api.agents.getAgents()

		data.value = response.data.agents || []
		emit("loaded", data.value)
		loading.value = false
	} catch (err) {
		if (!axios.isCancel(err)) {
			message.error(getApiErrorMessage(err as ApiError))
			loading.value = false
		}
	}
}, 400)

function handleCriticalAssetUpdated(payload: AgentCriticalUpdateSuccessPayload) {
	const agent = data.value.find(a => a.agent_id === payload.agentId)
	if (agent) {
		agent.critical_asset = payload.critical
	}
}

function resetPage() {
	pagination.value.page = 1
}

watch(
	loading,
	value => {
		emit("loading", value)
	},
	{ immediate: true }
)

watch([() => pagination.value.pageSize, filters], resetPage, {
	deep: true,
	immediate: true
})

onBeforeMount(() => {
	loadAgents()
})
</script>
