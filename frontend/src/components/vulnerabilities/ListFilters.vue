<template>
	<div class="alerts-filters flex flex-wrap gap-3">
		<div v-for="filter of filters" :key="filter.type">
			<n-input-group v-if="filter.type === 'customer_code'">
				<n-input-group-label size="small" class="flex! items-center gap-2">
					<Icon :name="CustomersIcon" />
					{{ getFilterLabel(filter.type) }}
				</n-input-group-label>
				<n-select
					v-model:value="filter.value"
					size="small"
					:options="customersOptions"
					placeholder="Select..."
					:loading="loadingCustomers"
					filterable
					class="w-50!"
					:consistent-menu-width="false"
				/>
				<n-button size="small" secondary tabindex="-1" @click="delFilter(filter.type)">
					<template #icon>
						<Icon :name="DelIcon" />
					</template>
				</n-button>
			</n-input-group>

			<n-input-group v-if="filter.type === 'severity'">
				<n-input-group-label size="small" class="flex! items-center gap-2">
					<Icon :name="SeverityIcon" />
					{{ getFilterLabel(filter.type) }}
				</n-input-group-label>
				<n-select
					v-model:value="filter.value"
					:options="severityOptions"
					placeholder="Select..."
					size="small"
					class="w-30!"
					:consistent-menu-width="false"
				/>
				<n-button size="small" secondary tabindex="-1" @click="delFilter(filter.type)">
					<template #icon>
						<Icon :name="DelIcon" />
					</template>
				</n-button>
			</n-input-group>

			<n-input-group v-if="filter.type === 'agent_name'">
				<n-input-group-label size="small" class="flex! items-center gap-2">
					<Icon :name="AgentsIcon" />
					{{ getFilterLabel(filter.type) }}
				</n-input-group-label>
				<n-select
					v-model:value="filter.value"
					:options="agentsOptions"
					placeholder="Select..."
					size="small"
					filterable
					class="w-50!"
					:loading="loadingAgents"
					:consistent-menu-width="false"
				/>
				<n-button size="small" secondary tabindex="-1" @click="delFilter(filter.type)">
					<template #icon>
						<Icon :name="DelIcon" />
					</template>
				</n-button>
			</n-input-group>

			<n-input-group
				v-if="filter.type === 'cve_id' && (typeof filter.value === 'string' || filter.value === null)"
			>
				<n-input-group-label size="small" class="flex! items-center gap-2">
					<Icon :name="SearchIcon" />
					{{ getFilterLabel(filter.type) }}
				</n-input-group-label>
				<n-input v-model:value="filter.value" autosize placeholder="Input..." size="small" class="min-w-60!" />
				<n-button size="small" secondary tabindex="-1" @click="delFilter(filter.type)">
					<template #icon>
						<Icon :name="DelIcon" />
					</template>
				</n-button>
			</n-input-group>

			<n-input-group
				v-if="filter.type === 'package_name' && (typeof filter.value === 'string' || filter.value === null)"
			>
				<n-input-group-label size="small" class="flex! items-center gap-2">
					<Icon :name="PackageIcon" />
					{{ getFilterLabel(filter.type) }}
				</n-input-group-label>
				<n-input v-model:value="filter.value" autosize placeholder="Input..." size="small" class="min-w-60!" />
				<n-button size="small" secondary tabindex="-1" @click="delFilter(filter.type)">
					<template #icon>
						<Icon :name="DelIcon" />
					</template>
				</n-button>
			</n-input-group>
		</div>

		<n-dropdown
			v-if="availableFilters.length"
			placement="bottom-start"
			trigger="click"
			:options="availableFilters"
			@select="addFilter"
		>
			<n-button size="small" dashed @click="load()">
				<template #icon>
					<Icon :name="AddIcon" />
				</template>
				<span v-if="!filters.length">Add filter</span>
			</n-button>
		</n-dropdown>

		<n-button v-if="filters.length && isDirty" size="small" secondary type="primary" @click="submit()">
			Submit
		</n-button>

		<n-button v-if="filters.length" size="small" quaternary @click="reset()">Reset</n-button>
	</div>
</template>

<script setup lang="ts">
import type { VulnerabilitiesFilterTypes, VulnerabilitiesListFilter } from "./types.d"
import type { Agent } from "@/types/agents.d"
import type { Customer } from "@/types/customers.d"
import _cloneDeep from "lodash/cloneDeep"
import _isEqual from "lodash/isEqual"
import { NButton, NDropdown, NInput, NInputGroup, NInputGroupLabel, NSelect, useMessage } from "naive-ui"
import { computed, onMounted, ref } from "vue"
import Api from "@/api"
import Icon from "@/components/common/Icon.vue"
import { VulnerabilitySeverity } from "@/types/vulnerabilities.d"

const emit = defineEmits<{
	(e: "submit", value: VulnerabilitiesListFilter[]): void
	(
		e: "mounted",
		value: {
			setFilter: (payload: VulnerabilitiesListFilter[]) => void
		}
	): void
}>()

const SearchIcon = "carbon:search"
const AgentsIcon = "carbon:network-3"
const PackageIcon = "carbon:package"
const CustomersIcon = "carbon:user-multiple"
const SeverityIcon = "carbon:warning"

const AddIcon = "carbon:add"
const DelIcon = "carbon:delete"
const message = useMessage()
const loadingAgents = ref(false)
const loadingCustomers = ref(false)
const agentsList = ref<Agent[]>([])
const customersList = ref<Customer[]>([])

const customersOptions = computed(() =>
	customersList.value.map(o => ({ label: `#${o.customer_code} - ${o.customer_name}`, value: o.customer_code }))
)

const agentsOptions = computed(() => agentsList.value.map(o => ({ label: o.hostname, value: o.hostname })))

const severityOptions = Object.values(VulnerabilitySeverity).map(severity => ({
	label: severity,
	value: severity
}))

const typeOptions: { label: string; value: VulnerabilitiesFilterTypes }[] = [
	{ label: "Customer", value: "customer_code" },
	{ label: "Severity", value: "severity" },
	{ label: "CVE", value: "cve_id" },
	{ label: "Agent", value: "agent_name" },
	{ label: "Package", value: "package_name" }
]

const filters = ref<VulnerabilitiesListFilter[]>([])
const lastFilters = ref<VulnerabilitiesListFilter[]>([])

const availableFilters = computed(() =>
	typeOptions
		.filter(o => !filters.value.map(f => f.type).includes(o.value))
		.map(t => ({ key: t.value, label: t.label }))
)

const isDirty = computed(() => !_isEqual(filters.value, lastFilters.value))

function getFilterLabel(type: VulnerabilitiesFilterTypes): string {
	return typeOptions.find(o => o.value === type)?.label || type
}

function addFilter(key: VulnerabilitiesFilterTypes) {
	filters.value.push({ type: key, value: null })
}

function delFilter(key: VulnerabilitiesFilterTypes) {
	filters.value = filters.value.filter(o => o.type !== key)
	submit()
}

function setFilter(newFilters: VulnerabilitiesListFilter[]) {
	for (const newFilter of newFilters) {
		const filterIndex = filters.value.findIndex(o => o.type === newFilter.type)

		if (filterIndex !== -1) {
			if (newFilter.value && filters.value[filterIndex]) {
				filters.value[filterIndex].value = newFilter.value
			} else {
				delFilter(newFilter.type)
			}
		} else if (newFilter.value) {
			filters.value.push(newFilter)
		}
	}
	submit()
}

function reset() {
	filters.value = []
	submit()
}

function submit() {
	lastFilters.value = _cloneDeep(filters.value)
	emit("submit", lastFilters.value)
}

function getAgents() {
	loadingAgents.value = true

	Api.agents
		.getAgents()
		.then(res => {
			if (res.data.success) {
				agentsList.value = res.data.agents || []
			} else {
				message.warning(res.data?.message || "Failed to load agents.")
			}
		})
		.catch(err => {
			message.error(err.response?.data?.message || "Failed to load agents.")
		})
		.finally(() => {
			loadingAgents.value = false
		})
}

function getCustomers() {
	loadingCustomers.value = true

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
			loadingCustomers.value = false
		})
}

function load() {
	getAgents()
	getCustomers()
}

onMounted(() => {
	emit("mounted", {
		setFilter
	})
})
</script>
