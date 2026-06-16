<template>
	<n-modal v-model:show="showModal" preset="card" title="Bulk Delete Agents" class="max-w-160!">
		<n-tabs v-model:value="activeTab" type="line">
			<n-tab-pane name="selection" tab="By Selection">
				<div class="tab-content">
					<n-alert v-if="!selectedAgents.length" type="warning" class="mb-4">
						No agents selected. Please select agents from the list first.
					</n-alert>
					<template v-else>
						<p class="mb-4">
							You are about to delete
							<strong>{{ selectedAgents.length }}</strong>
							selected agent(s).
						</p>
						<n-scrollbar class="mb-4 max-h-50">
							<div class="flex flex-wrap">
								<n-tag
									v-for="agent in selectedAgents"
									:key="agent.agent_id"
									closable
									class="mr-2 mb-2"
									@close="$emit('remove-selection', agent)"
								>
									{{ agent.hostname }} ({{ agent.agent_id }})
								</n-tag>
							</div>
						</n-scrollbar>
					</template>
				</div>
			</n-tab-pane>

			<n-tab-pane name="filter" tab="By Filter">
				<div class="tab-content">
					<n-form :model="filterForm" label-placement="top">
						<n-alert type="info" class="mb-4">
							At least one filter must be specified. This will delete all matching agents.
						</n-alert>

						<n-form-item label="Customer Code" path="customer_code">
							<n-select
								v-model:value="filterForm.customer_code"
								:options="customerOptions"
								placeholder="Select customer (optional)"
								clearable
								filterable
							/>
						</n-form-item>

						<n-form-item label="Agent Status" path="status">
							<n-select
								v-model:value="filterForm.status"
								:options="statusOptions"
								placeholder="Select status (optional)"
								clearable
							/>
						</n-form-item>

						<n-form-item label="Disconnected Days" path="disconnected_days">
							<n-input-number
								v-model:value="filterForm.disconnected_days"
								:min="1"
								:max="365"
								placeholder="Agents disconnected for more than X days"
								clearable
								class="w-full"
							/>
						</n-form-item>
					</n-form>
				</div>
			</n-tab-pane>
		</n-tabs>

		<template #footer>
			<n-space justify="end">
				<n-button @click="closeModal">Cancel</n-button>
				<n-button type="error" :loading :disabled="!canDelete" @click="confirmDelete">
					<template #icon>
						<Icon :name="DeleteIcon" />
					</template>
					Delete Agents
				</n-button>
			</n-space>
		</template>
	</n-modal>

	<!-- Confirmation Dialog -->
	<n-modal v-model:show="showConfirmDialog" preset="dialog" type="warning" title="Confirm Bulk Deletion">
		<template #default>
			<p>Are you sure you want to delete these agents?</p>
			<p class="mt-2 text-red-500">This action cannot be undone.</p>
			<template v-if="activeTab === 'filter'">
				<p class="mt-2">
					<strong>Filters:</strong>
				</p>
				<ul class="ml-4 list-disc">
					<li v-if="filterForm.customer_code">Customer: {{ filterForm.customer_code }}</li>
					<li v-if="filterForm.status">Status: {{ filterForm.status }}</li>
					<li v-if="filterForm.disconnected_days">
						Disconnected for: {{ filterForm.disconnected_days }}+ days
					</li>
				</ul>
			</template>
			<template v-else>
				<p class="mt-2">{{ selectedAgents.length }} agent(s) will be deleted.</p>
			</template>
		</template>
		<template #action>
			<n-button @click="showConfirmDialog = false">Cancel</n-button>
			<n-button type="error" :loading @click="executeDelete">Confirm Delete</n-button>
		</template>
	</n-modal>

	<!-- Results Modal -->
	<n-modal v-model:show="showResultsModal" preset="card" title="Deletion Results" class="max-w-140!">
		<div v-if="deleteResults" class="flex flex-col gap-4">
			<n-alert :type="deleteResults.success ? 'success' : 'warning'">
				{{ deleteResults.message }}
			</n-alert>

			<CardStatsBars
				v-if="deleteResults.total_requested > 0"
				title="Outcome"
				embedded
				:values="outcomeBarValues"
				show-zero-items
			/>

			<section v-if="deleteResults.results.length > 0">
				<h4 class="text-tertiary mb-3 text-xs font-medium tracking-wide uppercase">Deletion Details</h4>
				<n-scrollbar class="max-h-50">
					<div class="flex flex-col gap-2 pr-3">
						<CardEntity
							v-for="result in deleteResults.results"
							:key="result.agent_id"
							embedded
							:status="result.success ? 'success' : 'error'"
						>
							<template #headerMain>
								ID:
								<span class="text-default font-mono text-sm">{{ result.agent_id }}</span>
							</template>
							<template #headerExtra>
								<Badge
									type="splitted"
									bright
									class="text-default uppercase"
									size="small"
									:color="result.success ? 'success' : 'danger'"
								>
									<template #label>{{ result.success ? "Deleted" : "Failed" }}</template>
								</Badge>
							</template>
							<template #default>
								<div class="text-sm">{{ result.message }}</div>
							</template>
						</CardEntity>
					</div>
				</n-scrollbar>
			</section>
		</div>
		<template #footer>
			<n-space justify="end">
				<n-button @click="closeResultsModal">Close</n-button>
			</n-space>
		</template>
	</n-modal>
</template>

<script setup lang="ts">
import type { ItemProps } from "@/components/common/cards/CardStatsBars.vue"
import type { Agent, BulkDeleteAgentsResponse, BulkDeleteFilterRequest } from "@/types/agents.d"
import type { ApiError } from "@/types/common"
import {
	NAlert,
	NButton,
	NForm,
	NFormItem,
	NInputNumber,
	NModal,
	NScrollbar,
	NSelect,
	NSpace,
	NTabPane,
	NTabs,
	NTag,
	useMessage
} from "naive-ui"
import { computed, ref, watch } from "vue"
import Api from "@/api"
import Badge from "@/components/common/Badge.vue"
import CardEntity from "@/components/common/cards/CardEntity.vue"
import CardStats from "@/components/common/cards/CardStats.vue"
import CardStatsBars from "@/components/common/cards/CardStatsBars.vue"
import CardStatsIcon from "@/components/common/cards/CardStatsIcon.vue"
import Icon from "@/components/common/Icon.vue"
import { getApiErrorMessage } from "@/utils"

const props = defineProps<{
	show: boolean
	selectedAgents: Agent[]
	customers: string[]
}>()

const emit = defineEmits<{
	(e: "update:show", value: boolean): void
	(e: "remove-selection", agent: Agent): void
	(e: "deleted"): void
}>()

const message = useMessage()
const DeleteIcon = "carbon:trash-can"

const showModal = computed({
	get: () => props.show,
	set: value => emit("update:show", value)
})

const activeTab = ref<"selection" | "filter">("selection")
const loading = ref(false)
const showConfirmDialog = ref(false)
const showResultsModal = ref(false)
const deleteResults = ref<BulkDeleteAgentsResponse | null>(null)

const filterForm = ref<BulkDeleteFilterRequest>({
	customer_code: undefined,
	status: undefined,
	disconnected_days: undefined
})

const customerOptions = computed(() => {
	return props.customers.map(code => ({ label: code, value: code }))
})

const statusOptions = [
	{ label: "Disconnected", value: "disconnected" },
	{ label: "Never Connected", value: "never_connected" },
	{ label: "Active", value: "active" }
]

const hasFilters = computed(() => {
	return filterForm.value.customer_code || filterForm.value.status || filterForm.value.disconnected_days
})

const canDelete = computed(() => {
	if (activeTab.value === "selection") {
		return props.selectedAgents.length > 0
	}
	return hasFilters.value
})

const outcomeBarValues = computed<ItemProps[]>(() => {
	if (!deleteResults.value) return []

	return [
		{
			label: "Requested",
			value: deleteResults.value.total_requested,
			isTotal: true
		},
		{
			label: "Successful",
			value: deleteResults.value.successful_deletions,
			status: "success"
		},
		{
			label: "Failed",
			value: deleteResults.value.failed_deletions,
			status: "error"
		}
	]
})

function closeModal() {
	showModal.value = false
}

function closeResultsModal() {
	showResultsModal.value = false
	deleteResults.value = null
}

function confirmDelete() {
	showConfirmDialog.value = true
}

async function executeDelete() {
	showConfirmDialog.value = false
	loading.value = true
	deleteResults.value = null

	try {
		let response
		if (activeTab.value === "selection") {
			const agentIds = props.selectedAgents.map(a => a.agent_id)
			response = await Api.agents.bulkDeleteAgents(agentIds)
		} else {
			response = await Api.agents.bulkDeleteAgentsByFilter(filterForm.value)
		}

		deleteResults.value = response.data
		showModal.value = false

		if (response.data.success) {
			message.success(response.data.message)
			emit("deleted")
		} else {
			message.warning(response.data.message)
		}

		showResultsModal.value = true
	} catch (err) {
		message.error(getApiErrorMessage(err as ApiError) || "Failed to delete agents")
	} finally {
		loading.value = false
	}
}

// Reset form when modal closes
watch(showModal, newVal => {
	if (!newVal) {
		filterForm.value = {
			customer_code: undefined,
			status: undefined,
			disconnected_days: undefined
		}
	}
})

// Switch to selection tab if agents are selected
watch(
	() => props.selectedAgents.length,
	len => {
		if (len > 0) {
			activeTab.value = "selection"
		} else {
			activeTab.value = "filter"
		}
	},
	{ immediate: true }
)
</script>
