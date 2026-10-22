<template>
	<div class="mb-6 flex justify-end">
		<div>
			<n-input-group>
				<n-select
					v-model:value="filterUnit"
					:options="unitOptions"
					placeholder="Time unit"
					clearable
					class="w-28!"
				/>
				<n-input-number v-model:value="filterTime" :min="1" clearable placeholder="Time" class="w-32!" />
			</n-input-group>
		</div>
	</div>
	<n-spin :show="loading">
		<div class="flex min-h-52 flex-col gap-6">
			<n-collapse v-if="healthyList.length" :default-expanded-names="['healthy']">
				<n-collapse-item name="healthy">
					<template #header>
						<div class="text-primary flex items-center gap-2">
							<Icon :name="CheckIcon" :size="16" />
							Healthy
							<code>{{ healthyList.length }}</code>
						</div>
					</template>
					<div class="flex flex-col gap-2">
						<CustomerHealthcheckItem
							v-for="item of healthyList"
							:key="item.id"
							:health-data="item"
							:customer-code
							:source
							type="healthy"
							embedded
							class="item-appear item-appear-bottom item-appear-005"
						/>
					</div>
				</n-collapse-item>
			</n-collapse>
			<n-collapse v-if="unhealthyList.length" :default-expanded-names="['unhealthy']">
				<n-collapse-item name="unhealthy">
					<template #header>
						<div class="text-warning flex items-center gap-2">
							<Icon :name="AlertIcon" :size="16" />
							Unhealthy
							<code>{{ unhealthyList.length }}</code>
						</div>
					</template>
					<div class="flex flex-col gap-2">
						<!-- Pick unhealthy agents and delete them in one go (#1291). -->
						<div class="selection-bar" data-testid="healthcheck-selection-bar">
							<n-checkbox
								:checked="allSelected"
								:indeterminate="someSelected"
								data-testid="healthcheck-select-all"
								@update:checked="selectAll"
							>
								<span class="text-sm">Select all</span>
							</n-checkbox>
							<span
								class="selection-count font-mono tabular-nums"
								data-testid="healthcheck-selected-count"
							>
								<span :class="selectedIds.size ? 'text-default' : ''">{{ selectedIds.size }}</span>
								/ {{ unhealthyList.length }} selected
							</span>
							<div class="ml-auto flex items-center gap-1.5">
								<n-button v-if="selectedIds.size" size="small" quaternary @click="clearSelection">
									Clear
								</n-button>
								<n-button
									size="small"
									type="error"
									ghost
									:disabled="!selectedIds.size"
									:title="selectedIds.size ? undefined : 'Select the agents to delete first'"
									data-testid="healthcheck-delete-selected"
									@click="showDelete = true"
								>
									<template #icon><Icon :name="TrashIcon" :size="14" /></template>
									Delete selected
								</n-button>
							</div>
						</div>
						<CustomerHealthcheckItem
							v-for="item of unhealthyList"
							:key="item.id"
							:health-data="item"
							:customer-code
							:source
							type="unhealthy"
							embedded
							selectable
							:selected="selectedIds.has(item.agent_id)"
							class="item-appear item-appear-bottom item-appear-005"
							@update:selected="value => setSelected(item.agent_id, value)"
						/>
					</div>
				</n-collapse-item>
			</n-collapse>
			<n-empty v-if="!healthyList.length && !unhealthyList.length && !loading" class="h-48 justify-center" />
		</div>
	</n-spin>

	<UnhealthyAgentsDeleteDialog
		v-model:show="showDelete"
		:source
		:customer-code
		:agents="selectedAgents"
		:list-filter="loadedFilter"
		@deleted="onDeleted"
	/>
</template>

<script setup lang="ts">
import type { CustomerAgentsHealthcheckQuery } from "@/api/endpoints/customers"
import type { ApiCommonResponse, ApiError } from "@/types/common"
import type { CustomerAgentHealth, CustomerHealthcheckSource } from "@/types/customers"
import { watchDebounced } from "@vueuse/core"
import _get from "lodash/get"
import {
	NButton,
	NCheckbox,
	NCollapse,
	NCollapseItem,
	NEmpty,
	NInputGroup,
	NInputNumber,
	NSelect,
	NSpin,
	useMessage
} from "naive-ui"
import { computed, onBeforeMount, ref, watch } from "vue"
import Api from "@/api"
import Icon from "@/components/common/Icon.vue"
import { getApiErrorMessage } from "@/utils"
import CustomerHealthcheckItem from "./CustomerHealthcheckItem.vue"
import UnhealthyAgentsDeleteDialog from "./UnhealthyAgentsDeleteDialog.vue"

const props = defineProps<{
	source: CustomerHealthcheckSource
	customerCode: string
	filters: Partial<{ time: number; unit: "minutes" | "hours" | "days" }>
}>()

const emit = defineEmits<{
	(e: "update:filters", value: Partial<{ time: number; unit: "minutes" | "hours" | "days" }>): void
}>()

const { source, customerCode } = props

const CheckIcon = "carbon:checkmark-outline"
const AlertIcon = "mdi:alert-outline"
const TrashIcon = "carbon:trash-can"

const loading = ref(false)
const healthyList = ref<CustomerAgentHealth[]>([])
const unhealthyList = ref<CustomerAgentHealth[]>([])
const message = useMessage()

// ── selection for a bulk deletion (#1291) ─────────────────────────────────────────────────────
const selectedIds = ref(new Set<string>())
const showDelete = ref(false)
/** The filter the shown list was read with, not the one being typed: the dialog starts from it. */
const loadedFilter = ref<Partial<{ time: number; unit: "minutes" | "hours" | "days" }>>({})

const selectedAgents = computed(() => unhealthyList.value.filter(agent => selectedIds.value.has(agent.agent_id)))
const allSelected = computed(
	() => !!unhealthyList.value.length && selectedIds.value.size === unhealthyList.value.length
)
const someSelected = computed(() => selectedIds.value.size > 0 && !allSelected.value)

function setSelected(agentId: string, value: boolean) {
	const next = new Set(selectedIds.value)
	if (value) next.add(agentId)
	else next.delete(agentId)
	selectedIds.value = next
}

function selectAll(value: boolean) {
	selectedIds.value = value ? new Set(unhealthyList.value.map(agent => agent.agent_id)) : new Set()
}

function clearSelection() {
	selectedIds.value = new Set()
}

/** Keep only what the list still shows as unhealthy: a selection never outlives its rows. */
function pruneSelection() {
	const shown = new Set(unhealthyList.value.map(agent => agent.agent_id))
	selectedIds.value = new Set([...selectedIds.value].filter(id => shown.has(id)))
}

/** A deletion ends the selection: what was kept had a reason, and must be picked again on purpose. */
function onDeleted() {
	clearSelection()
	getList()
}

const unitOptions = [
	{ label: "Minutes", value: "minutes" },
	{ label: "Hours", value: "hours" },
	{ label: "Days", value: "days" }
]

const filters = computed({
	get: () => props.filters,
	set: value => emit("update:filters", value)
})

const filterTime = computed({
	get: () => props.filters.time,
	set: value => emit("update:filters", { ...props.filters, time: value })
})

const filterUnit = computed({
	get: () => props.filters.unit,
	set: value => emit("update:filters", { ...props.filters, unit: value })
})

function buildHealthcheckQuery(): CustomerAgentsHealthcheckQuery | undefined {
	if (filters.value.time && filters.value.unit) {
		return { [filters.value.unit]: filters.value.time }
	}

	return undefined
}

function getList() {
	let apiCall: Promise<ApiCommonResponse> | null = null
	let healthyKey = ""
	let unhealthyKey = ""

	switch (source) {
		case "wazuh":
			apiCall = Api.customers.getCustomerAgentsHealthcheckWazuh({
				code: customerCode,
				...buildHealthcheckQuery()
			})
			healthyKey = "healthy_wazuh_agents"
			unhealthyKey = "unhealthy_wazuh_agents"
			break
		case "velociraptor":
			apiCall = Api.customers.getCustomerAgentsHealthcheckVelociraptor({
				code: customerCode,
				...buildHealthcheckQuery()
			})
			healthyKey = "healthy_velociraptor_agents"
			unhealthyKey = "unhealthy_velociraptor_agents"
			break
	}

	if (!apiCall) {
		return
	}

	loading.value = true
	const filterAtLoad = { ...filters.value }

	apiCall
		.then(res => {
			if (res.data.success) {
				healthyList.value = _get(res, `data.${healthyKey}`, [])
				unhealthyList.value = _get(res, `data.${unhealthyKey}`, [])
				loadedFilter.value = filterAtLoad
				pruneSelection()
			} else {
				message.warning(res.data?.message || "An error occurred. Please try again later.")
			}
		})
		.catch(err => {
			message.error(getApiErrorMessage(err as ApiError) || "An error occurred. Please try again later.")
		})
		.finally(() => {
			loading.value = false
		})
}

watchDebounced(
	() => filters.value.time,
	() => {
		if ((filters.value.time && filters.value.unit) || (!filters.value.time && !filters.value.unit)) {
			getList()
		}
	},
	{ debounce: 500 }
)
watch(
	() => filters.value.unit,
	() => {
		if ((filters.value.time && filters.value.unit) || (!filters.value.time && !filters.value.unit)) {
			getList()
		}
	}
)

onBeforeMount(() => {
	getList()
})
</script>

<style scoped>
.selection-bar {
	display: flex;
	flex-wrap: wrap;
	align-items: center;
	gap: calc(var(--spacing) * 2) calc(var(--spacing) * 4);
	padding: calc(var(--spacing) * 2) calc(var(--spacing) * 3);
	border: 1px solid var(--border-color);
	border-radius: var(--border-radius);
	background-color: var(--bg-secondary-color);
}

.selection-count {
	font-size: 10px;
	letter-spacing: 0.12em;
	text-transform: uppercase;
	color: var(--fg-tertiary-color);
}
</style>
