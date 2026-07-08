<template>
	<n-card class="agent-toolbar @container w-full max-w-full min-w-85 overflow-hidden" content-class="p-0!">
		<div class="flex h-full flex-col gap-6 overflow-hidden px-4 py-3">
			<div class="flex flex-col gap-3">
				<div class="flex items-center justify-between gap-2">
					<div class="text-secondary">
						<strong v-if="agentsFilteredLength !== agentsLength">{{ agentsFilteredLength }}</strong>
						<span v-if="agentsFilteredLength !== agentsLength">/</span>
						<strong class="font-mono">{{ agentsLength }}</strong>
						Agents
					</div>

					<n-dropdown
						v-if="enableSyncVulnerabilitiesDropdown"
						placement="bottom-start"
						trigger="click"
						:options="syncDropdownOptions"
						@select="emit('run', $event)"
					>
						<n-button :loading="syncing" secondary size="small" @click="load()">Sync</n-button>
					</n-dropdown>
					<n-button v-else :loading="syncing" secondary size="small" @click="emit('run', 'sync-agents')">
						Sync
					</n-button>
				</div>
				<n-input v-model:value="textFilter" placeholder="Search for an agent" clearable>
					<template #prefix>
						<Icon :name="SearchIcon" />
					</template>
				</n-input>
				<n-form-item label="Customer" :show-feedback="false" class="mt-2 mb-0!">
					<n-select
						v-model:value="customerCodes"
						:options="customersOptions"
						:loading="loadingCustomersList"
						placeholder="All customers"
						multiple
						filterable
						clearable
						size="small"
					/>
				</n-form-item>
			</div>

			<!-- Selection Mode & Bulk Delete Section -->
			<n-card embedded content-class="flex flex-col gap-3" size="small" class="hidden! lg:flex!">
				<div v-if="!hideSelectionSwitch" class="flex items-center gap-2">
					<n-switch v-model:value="selectionMode" @update:value="emit('update:selection-mode', $event)">
						<template #checked>Selection ON</template>
						<template #unchecked>Selection OFF</template>
					</n-switch>
				</div>

				<p v-if="selectionMode" class="text-secondary-color text-xs">
					Click agents to select them for bulk operations. Or select "Bulk Delete" and apply a filter to
					delete multiple agents at once.
				</p>

				<div class="flex items-center justify-between gap-2">
					<n-button type="error" secondary size="small" :disabled="syncing" @click="emit('bulk-delete')">
						<template #icon>
							<Icon :name="DeleteIcon" />
						</template>
						{{ selectedCount ? `Delete ${selectedCount}` : "Bulk Delete" }}
					</n-button>

					<div v-if="selectedCount && selectedCount > 0">
						<n-button size="small" quaternary @click="emit('clear-selection')">Clear</n-button>
					</div>
				</div>
			</n-card>

			<div class="hidden grow flex-col overflow-hidden lg:flex">
				<n-scrollbar>
					<div v-if="agentsCritical?.length" class="mb-5">
						<div class="mb-2">
							Critical Assets
							<small class="text-secondary font-mono">({{ agentsCritical.length }})</small>
						</div>
						<div class="flex flex-col gap-2">
							<n-tag
								v-for="agent in agentsCritical"
								:key="agent.agent_id"
								type="error"
								:bordered="false"
								class="cursor-pointer!"
								@click="emit('click', agent)"
							>
								{{ agent.hostname }}
							</n-tag>
						</div>
					</div>
					<div v-if="agentsOnline?.length">
						<div class="mb-2">
							Online Agents
							<small class="text-secondary font-mono">({{ agentsOnline.length }})</small>
						</div>
						<div class="flex flex-col gap-2">
							<n-tag
								v-for="agent in agentsOnline"
								:key="agent.agent_id"
								type="success"
								:bordered="false"
								class="cursor-pointer!"
								@click="emit('click', agent)"
							>
								{{ agent.hostname }}
							</n-tag>
						</div>
					</div>
				</n-scrollbar>
			</div>
		</div>
	</n-card>
</template>

<script setup lang="ts">
import type { DropdownMixedOption } from "naive-ui/es/dropdown/src/interface"
import type { Agent } from "@/types/agents"
import type { ApiError } from "@/types/common"
import type { Customer } from "@/types/customers"
import { useWindowSize } from "@vueuse/core"
import { NButton, NCard, NDropdown, NFormItem, NInput, NScrollbar, NSelect, NSwitch, NTag, useMessage } from "naive-ui"
import { computed, h, onBeforeMount, ref, toRefs } from "vue"
import Api from "@/api"
import Icon from "@/components/common/Icon.vue"
import { useGlobalCustomerFilter } from "@/composables/useGlobalCustomerFilter"
import { getApiErrorMessage } from "@/utils"

const props = defineProps<{
	modelValue: string
	syncing?: boolean
	enableSyncVulnerabilitiesDropdown?: boolean
	agentsLength?: number
	agentsFilteredLength?: number
	agentsCritical?: Agent[]
	agentsOnline?: Agent[]
	selectedCount?: number
	hideSelectionSwitch?: boolean
}>()

const emit = defineEmits<{
	(e: "run", value: "sync-agents" | `sync-vulnerabilities:${string}`): void
	(e: "update:modelValue", value: string): void
	(e: "click", value: Agent): void
	(e: "bulk-delete"): void
	(e: "update:selection-mode", value: boolean): void
	(e: "clear-selection"): void
}>()

const {
	modelValue,
	syncing,
	agentsLength,
	agentsFilteredLength,
	agentsCritical,
	agentsOnline,
	enableSyncVulnerabilitiesDropdown,
	selectedCount,
	hideSelectionSwitch
} = toRefs(props)

const SearchIcon = "carbon:search"
const DeleteIcon = "carbon:trash-can"
const message = useMessage()
const { applyGlobalCustomerPrefill } = useGlobalCustomerFilter()

const customerCodes = defineModel<string[]>("customerCodes", { default: () => [] })

const textFilter = computed<string>({
	get() {
		return modelValue.value
	},
	set(value) {
		emit("update:modelValue", value)
	}
})

const selectionMode = defineModel<boolean>("selectionMode", { default: true, required: false })

const loadingCustomersList = ref(false)
const customersList = ref<Customer[]>([])
const { width: winWidth } = useWindowSize()

const customersOptions = computed(() =>
	customersList.value.map(o => ({ label: `#${o.customer_code} - ${o.customer_name}`, value: o.customer_code }))
)

const syncDropdownOptions = computed(() => {
	const options: DropdownMixedOption[] = [
		{
			label: "Sync Agents",
			key: "sync-agents"
		}
	]

	if (winWidth.value > 550) {
		options.push({
			label: `Sync Agent Vulnerabilities${loadingCustomersList.value ? "..." : ""}`,
			key: "sync-vulnerabilities",
			disabled: loadingCustomersList.value,
			children: loadingCustomersList.value
				? undefined
				: [
						{
							label: () => h("div", { class: "pl-2" }, "Select a Customer"),
							type: "group",
							children: customersList.value.map(o => ({
								label: `#${o.customer_code} - ${o.customer_name}`,
								key: `sync-vulnerabilities:${o.customer_code}`
							}))
						}
					]
		})
	} else {
		options.push({
			label: () => h("div", { class: "pl-2" }, "Select a Customer"),
			type: "group",
			children: customersList.value.map(o => ({
				label: `#${o.customer_code} - ${o.customer_name}`,
				key: `sync-vulnerabilities:${o.customer_code}`
			}))
		})
	}

	return options
})

function getCustomers() {
	loadingCustomersList.value = true

	Api.customers
		.getCustomers()
		.then(res => {
			if (res.data.success) {
				customersList.value = res.data?.customers || []
			} else {
				message.warning(res.data?.message || "An error occurred. Please try again later.")
			}
		})
		.catch(err => {
			message.error(getApiErrorMessage(err as ApiError) || "An error occurred. Please try again later.")
		})
		.finally(() => {
			loadingCustomersList.value = false
		})
}

function load() {
	if (!customersList.value.length) {
		getCustomers()
	}
}

onBeforeMount(() => {
	getCustomers()
	const draft = { customerCodes: customerCodes.value }
	applyGlobalCustomerPrefill("customerCodes", draft, { multiple: true })
	customerCodes.value = (draft.customerCodes as string[]) || []
})
</script>
