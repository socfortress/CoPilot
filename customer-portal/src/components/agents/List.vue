<template>
	<div class="flex flex-col gap-6">
		<Filters v-model:value="filters" :status="statusesList" :os="osList" />

		<div class="flex flex-col gap-2">
			<div ref="headerRef" class="flex items-center justify-between">
				<Chip size="small" :value="loading ? 'Loading...' : paginatedTotal" label="items" />

				<div class="flex items-center gap-2 whitespace-nowrap">
					<n-button
						size="small"
						secondary
						:disabled="loading || exporting || !paginatedTotal"
						:loading="exporting"
						:focusable="false"
						@click="exportCsv"
					>
						<template #icon>
							<Icon name="carbon:download" />
						</template>
						Export CSV
					</n-button>

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
					data-testid="agents-table"
					bordered
					:loading
					size="small"
					:data
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
import type { Agent, AgentsStats, AgentStatus } from "@/types/agents"
import type { ApiError } from "@/types/common"
import { refDebounced, useElementSize } from "@vueuse/core"
import axios from "axios"
import { saveAs } from "file-saver"
import { NButton, NDataTable, NEmpty, NPagination, NTag, useMessage } from "naive-ui"
import { computed, ref, toRef, useTemplateRef, watch } from "vue"
import Api from "@/api"
import Filters from "@/components/agents/Filters.vue"
import Chip from "@/components/common/Chip.vue"
import Icon from "@/components/common/Icon.vue"
import { usePaginatedLoad } from "@/composables/common/usePaginatedLoad"
import { useCustomerFilterStore } from "@/stores/customerFilter"
import { useSettingsStore } from "@/stores/settings"
import { getApiErrorMessage, getStatusColor } from "@/utils"
import { formatDate } from "@/utils/format"
import AgentCriticalSelect from "./AgentCriticalSelect.vue"
import AgentDetailsButton from "./AgentDetailsButton.vue"

const emit = defineEmits<{
	(e: "stats", value: AgentsStats): void
	(e: "loading", value: boolean): void
}>()

const message = useMessage()
const loading = ref(false)
const exporting = ref(false)
const dFormats = useSettingsStore().dateFormat
const customerFilterStore = useCustomerFilterStore()

const { width: headerWidthRef } = useElementSize(useTemplateRef("headerRef"))
const pageSizes = [10, 25, 50, 100]
const pageSlot = computed(() => (headerWidthRef.value < 800 ? 5 : 8))
const simpleMode = computed(() => headerWidthRef.value < 600)
const showSizePicker = ref(true)

const pagination = ref({
	page: 1,
	pageSize: pageSizes[1] ?? 25
})

const filters = ref<AgentsFilters>({
	status: null,
	os: null,
	critical: false,
	search: null
})

// Paging, counting and filtering all happen on the server (GET /customer_portal/agents):
// the browser holds one page, never the whole fleet. Only the typed search is debounced.
const search = refDebounced(
	computed(() => filters.value.search?.trim() || null),
	400
)

const data = ref<Agent[]>([])
const paginatedTotal = ref(0)
const statusesList = ref<AgentStatus[]>([])
const osList = ref<string[]>([])

function query() {
	return {
		search: search.value,
		status: filters.value.status,
		os: filters.value.os,
		critical: filters.value.critical,
		customerCodes: customerFilterStore.queryCustomerCodes
	}
}

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

async function loadAgents() {
	loading.value = true

	abortController.abort()
	abortController = new AbortController()

	try {
		const response = await Api.agents.getAgentsPage(
			{ ...query(), page: pagination.value.page, pageSize: pagination.value.pageSize },
			abortController.signal
		)

		data.value = response.data.agents || []
		paginatedTotal.value = response.data.total
		statusesList.value = response.data.statuses
		osList.value = response.data.os_list
		emit("stats", response.data.stats)
		loading.value = false
	} catch (err) {
		if (!axios.isCancel(err)) {
			message.error(getApiErrorMessage(err as ApiError))
			loading.value = false
		}
	}
}

async function exportCsv() {
	// Every agent matching the filters, not only the page on screen.
	exporting.value = true
	try {
		const response = await Api.agents.exportAgents(query())
		const stamp = new Date().toISOString().slice(0, 19).replace(/[:T]/g, "-")
		saveAs(response.data, `assets-export-${stamp}.csv`)
		message.success(`Exported ${paginatedTotal.value} asset${paginatedTotal.value === 1 ? "" : "s"} to CSV`)
	} catch (err) {
		message.error(getApiErrorMessage(err as ApiError))
	} finally {
		exporting.value = false
	}
}

function handleCriticalAssetUpdated(payload: AgentCriticalUpdateSuccessPayload) {
	const agent = data.value.find(a => a.agent_id === payload.agentId)
	if (agent) {
		agent.critical_asset = payload.critical
	}
	// The critical count in the cards (and a "critical only" page) now differ.
	loadAgents()
}

watch(
	loading,
	value => {
		emit("loading", value)
	},
	{ immediate: true }
)

usePaginatedLoad({
	page: toRef(pagination.value, "page"),
	resetOn: [
		() => pagination.value.pageSize,
		search,
		() => filters.value.status,
		() => filters.value.os,
		() => filters.value.critical,
		() => customerFilterStore.queryCustomerCodes
	],
	load: loadAgents
})
</script>
