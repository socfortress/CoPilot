<template>
	<n-card class="agent-toolbar" content-class="p-0!">
		<div class="wrapper flex flex-col gap-6 px-4 py-3">
			<div class="flex flex-col gap-2">
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
						:options="customersOptions"
						@select="emit('run', $event)"
					>
						<n-button :loading="syncing" secondary @click="load()">Sync</n-button>
					</n-dropdown>
					<n-button v-else :loading="syncing" secondary @click="emit('run', 'sync-agents')">Sync</n-button>
				</div>
				<div class="agent-search flex gap-3">
					<n-input v-model:value="textFilter" placeholder="Search for an agent" clearable>
						<template #prefix>
							<Icon :name="SearchIcon" />
						</template>
					</n-input>
				</div>
			</div>

			<!-- Selection Mode & Bulk Delete Section -->
			<n-card embedded content-class="flex flex-col gap-3" size="small">
				<div v-if="!hideSelectionSwitch" class="selection-toggle flex items-center gap-2">
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
					<n-button
						type="error"
						secondary
						size="small"
						:disabled="syncing || !selectedCount"
						@click="emit('bulk-delete')"
					>
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

			<div class="agents-list flex grow flex-col overflow-hidden">
				<n-scrollbar>
					<div v-if="agentsCritical?.length" class="agents-critical-list">
						<div class="title">
							Critical Assets
							<small class="text-secondary font-mono">({{ agentsCritical.length }})</small>
						</div>
						<div class="list">
							<div
								v-for="agent in agentsCritical"
								:key="agent.agent_id"
								class="item"
								@click="emit('click', agent)"
							>
								{{ agent.hostname }}
							</div>
						</div>
					</div>
					<div v-if="agentsOnline?.length" class="agents-online-list">
						<div class="title">
							Online Agents
							<small class="text-secondary font-mono">({{ agentsOnline.length }})</small>
						</div>
						<div class="list">
							<div
								v-for="agent in agentsOnline"
								:key="agent.agent_id"
								class="item"
								@click="emit('click', agent)"
							>
								{{ agent.hostname }}
							</div>
						</div>
					</div>
				</n-scrollbar>
			</div>
		</div>
	</n-card>
</template>

<script setup lang="ts">
// TODO-FE: refactor
import type { DropdownMixedOption } from "naive-ui/es/dropdown/src/interface"
import type { Agent } from "@/types/agents.d"
import type { Customer } from "@/types/customers.d"
import { useWindowSize } from "@vueuse/core"
import { NButton, NCard, NDropdown, NInput, NScrollbar, NSwitch, NTag, useMessage } from "naive-ui"
import { computed, h, ref, toRefs } from "vue"
import Api from "@/api"
import Icon from "@/components/common/Icon.vue"

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

const customersOptions = computed(() => {
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
			message.error(err.response?.data?.message || "An error occurred. Please try again later.")
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
</script>

<style lang="scss" scoped>
.agent-toolbar {
	container-type: inline-size;
	overflow: hidden;
	max-width: 100%;
	min-width: 340px;

	.wrapper {
		overflow: hidden;
		height: 100%;

		.agents-list {
			.title {
				margin-bottom: calc(var(--spacing) * 2);
			}

			.list {
				.item {
					border: 2px solid transparent;
					padding-inline: calc(var(--spacing) * 3);
					padding-block: calc(var(--spacing) * 2);
					font-size: 14px;
					font-weight: bold;
					cursor: pointer;
					border-radius: var(--border-radius);

					&:not(:last-child) {
						margin-bottom: calc(var(--spacing) * 2);
					}

					&:hover {
						background-color: var(--hover-color);
					}
				}
			}

			.agents-critical-list {
				margin-bottom: calc(var(--spacing) * 5);

				.list {
					.item {
						border-color: var(--warning-color);
					}
				}
			}
			.agents-online-list {
				.list {
					.item {
						border-color: var(--success-color);
					}
				}
			}
		}
	}

	@container (min-width: 350px) {
		.wrapper {
			.agent-search {
				flex-grow: 1;
			}
			.search-info {
				display: none;
			}
			.agents-list {
				display: none;
			}
		}
	}
	@media (max-width: 500px) {
		min-width: 100%;

		.wrapper {
			.agent-search {
				flex-grow: 1;
				width: 100%;
			}
			.search-info {
				display: none;
			}
			.agents-list {
				display: none;
			}
		}
	}
}
</style>
