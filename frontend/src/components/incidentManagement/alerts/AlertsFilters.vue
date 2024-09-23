<template>
	<div class="alerts-filters flex flex-wrap gap-3">
		<div v-for="filter of filters" :key="filter.type">
			<n-input-group v-if="filter.type === 'status'">
				<n-select
					v-model:value="filter.value"
					size="small"
					:options="statusOptions"
					placeholder="Status..."
					class="!w-32"
				/>
				<n-button size="small" secondary @click="delFilter(filter.type)">
					<template #icon>
						<Icon :name="DelIcon" />
					</template>
				</n-button>
			</n-input-group>

			<n-input-group v-if="filter.type === 'assignedTo'">
				<n-select
					v-model:value="filter.value"
					:options="usersOptions"
					placeholder="Assigned to..."
					size="small"
					filterable
					class="!w-40"
				/>
				<n-button size="small" secondary @click="delFilter(filter.type)">
					<template #icon>
						<Icon :name="DelIcon" />
					</template>
				</n-button>
			</n-input-group>

			<n-input-group v-if="filter.type === 'customerCode'">
				<n-select
					v-model:value="filter.value"
					:options="customersOptions"
					placeholder="Customer..."
					size="small"
					filterable
					class="!w-56"
				/>
				<n-button size="small" secondary @click="delFilter(filter.type)">
					<template #icon>
						<Icon :name="DelIcon" />
					</template>
				</n-button>
			</n-input-group>

			<n-select
				v-else-if="filter.type === 'source'"
				v-model:value="filter.value"
				:options="sourcesOptions"
				placeholder="Source..."
				size="small"
				filterable
				class="!w-44"
			/>
			<n-select
				v-else-if="filter.type === 'tag'"
				v-model:value="filter.value"
				filterable
				multiple
				tag
				size="small"
				autosize
				placeholder="Tags..."
				:show-arrow="false"
				:show="false"
				class="!min-w-40"
			/>
			<n-input
				v-else-if="filter.type === 'title'"
				v-model:value="filter.value"
				autosize
				placeholder="Title..."
				size="small"
				class="!min-w-40"
			/>
			<n-input
				v-else-if="filter.type === 'assetName'"
				v-model:value="filter.value"
				autosize
				placeholder="Asset..."
				size="small"
				class="!min-w-40"
			/>
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
				Add filter
			</n-button>
		</n-dropdown>

		<n-button v-if="filters.length" size="small" quaternary @click="reset()">Reset</n-button>
	</div>
</template>

<script setup lang="ts">
import type { AlertsFilterTypes } from "@/api/endpoints/incidentManagement"
import type { Customer } from "@/types/customers.d"
import type { AlertStatus } from "@/types/incidentManagement/alerts.d"
import type { SourceName } from "@/types/incidentManagement/sources.d"
import Api from "@/api"
import Icon from "@/components/common/Icon.vue"
import _cloneDeep from "lodash/cloneDeep"
import _orderBy from "lodash/orderBy"
import { NButton, NDropdown, NInput, NInputGroup, NSelect, useMessage } from "naive-ui"
import { computed, inject, ref, type Ref } from "vue"

export interface AlertsListFilter {
	type: AlertsFilterTypes
	value: string | AlertStatus | null
}

const AddIcon = "carbon:add"
const DelIcon = "carbon:delete"
const message = useMessage()
const availableUsers = inject<Ref<string[]>>("assignable-users", ref([]))
const configuredSourcesList = ref<SourceName[]>([])
const customersList = ref<Customer[]>([])
const usersOptions = computed(() => availableUsers.value.map(o => ({ label: o, value: o })))
const customersOptions = computed(() =>
	customersList.value.map(o => ({ label: `#${o.customer_code} - ${o.customer_name}`, value: o.customer_code }))
)
const sourcesOptions = computed(() => configuredSourcesList.value.map(o => ({ label: o, value: o })))
const statusOptions: { label: string; value: AlertStatus }[] = [
	{ label: "Open", value: "OPEN" },
	{ label: "Closed", value: "CLOSED" },
	{ label: "In progress", value: "IN_PROGRESS" }
]

const typeOptions: { label: string; value: AlertsFilterTypes }[] = [
	{ label: "Status", value: "status" },
	{ label: "Asset Name", value: "assetName" },
	{ label: "Assigned To", value: "assignedTo" },
	{ label: "Tag", value: "tag" },
	{ label: "Title", value: "title" },
	{ label: "Customer Code", value: "customerCode" },
	{ label: "Source", value: "source" }
]

const filters = ref<AlertsListFilter[]>([])
const availableFilters = computed(() =>
	typeOptions
		.filter(o => !filters.value.map(f => f.type).includes(o.value))
		.map(t => ({ key: t.value, label: t.label }))
)

function addFilter(key: AlertsFilterTypes) {
	filters.value.push({ type: key, value: null })
}

function delFilter(key: AlertsFilterTypes) {
	filters.value = filters.value.filter(o => o.type !== key)
}

function reset() {
	filters.value = []
}

function getAvailableUsers() {
	Api.incidentManagement
		.getAvailableUsers()
		.then(res => {
			if (res.data.success) {
				availableUsers.value = res.data?.available_users || []
			} else {
				message.warning(res.data?.message || "An error occurred. Please try again later.")
			}
		})
		.catch(err => {
			message.error(err.response?.data?.message || "An error occurred. Please try again later.")
		})
}

function getCustomers() {
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
}

function getConfiguredSources() {
	Api.incidentManagement
		.getConfiguredSources()
		.then(res => {
			if (res.data.success) {
				configuredSourcesList.value = res.data?.sources || []
			} else {
				message.warning(res.data?.message || "An error occurred. Please try again later.")
			}
		})
		.catch(err => {
			message.error(err.response?.data?.message || "An error occurred. Please try again later.")
		})
}

function load() {
	if (!availableUsers.value.length) {
		getAvailableUsers()
	}
	if (!customersList.value.length) {
		getCustomers()
	}
	if (!configuredSourcesList.value.length) {
		getConfiguredSources()
	}
}
</script>

<style lang="scss" scoped></style>
