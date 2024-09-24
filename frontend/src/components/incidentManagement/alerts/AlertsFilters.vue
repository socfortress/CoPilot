<template>
	<div class="alerts-filters flex flex-wrap gap-3">
		<div v-for="filter of filters" :key="filter.type">
			<n-input-group v-if="filter.type === 'status'">
				<n-input-group-label size="small">{{ filter.label }}</n-input-group-label>
				<n-select
					v-model:value="filter.value"
					size="small"
					:options="statusOptions"
					placeholder="Select..."
					class="!w-32"
				/>
				<n-button size="small" secondary tabindex="-1" @click="delFilter(filter.type)">
					<template #icon>
						<Icon :name="DelIcon" />
					</template>
				</n-button>
			</n-input-group>

			<n-input-group v-if="filter.type === 'assignedTo'">
				<n-input-group-label size="small">{{ filter.label }}</n-input-group-label>
				<n-select
					v-model:value="filter.value"
					:options="usersOptions"
					placeholder="Select..."
					size="small"
					filterable
					class="!w-40"
					:loading="loadingAvailableUsers || !usersOptions.length"
				/>
				<n-button size="small" secondary tabindex="-1" @click="delFilter(filter.type)">
					<template #icon>
						<Icon :name="DelIcon" />
					</template>
				</n-button>
			</n-input-group>

			<n-input-group v-if="filter.type === 'customerCode'">
				<n-input-group-label size="small">{{ filter.label }}</n-input-group-label>
				<n-select
					v-model:value="filter.value"
					:options="customersOptions"
					placeholder="Select..."
					size="small"
					filterable
					class="!w-56"
					:loading="loadingCustomers || !customersOptions.length"
				/>
				<n-button size="small" secondary tabindex="-1" @click="delFilter(filter.type)">
					<template #icon>
						<Icon :name="DelIcon" />
					</template>
				</n-button>
			</n-input-group>

			<n-input-group v-if="filter.type === 'source'">
				<n-input-group-label size="small">{{ filter.label }}</n-input-group-label>
				<n-select
					v-model:value="filter.value"
					:options="sourcesOptions"
					placeholder="Select..."
					size="small"
					filterable
					class="!w-44"
					:loading="loadingConfiguredSources || !sourcesOptions.length"
				/>
				<n-button size="small" secondary tabindex="-1" @click="delFilter(filter.type)">
					<template #icon>
						<Icon :name="DelIcon" />
					</template>
				</n-button>
			</n-input-group>

			<n-input-group v-if="filter.type === 'tag'">
				<n-input-group-label size="small">{{ filter.label }}</n-input-group-label>
				<n-select
					v-model:value="filter.value"
					filterable
					multiple
					tag
					size="small"
					autosize
					placeholder="Input, press enter to create"
					:show-arrow="false"
					:show="false"
					class="!min-w-64"
				/>
				<n-button size="small" secondary tabindex="-1" @click="delFilter(filter.type)">
					<template #icon>
						<Icon :name="DelIcon" />
					</template>
				</n-button>
			</n-input-group>

			<n-input-group v-if="filter.type === 'title'">
				<n-input-group-label size="small">{{ filter.label }}</n-input-group-label>
				<n-input v-model:value="filter.value" autosize placeholder="Input..." size="small" class="!min-w-40" />
				<n-button size="small" secondary tabindex="-1" @click="delFilter(filter.type)">
					<template #icon>
						<Icon :name="DelIcon" />
					</template>
				</n-button>
			</n-input-group>

			<n-input-group v-if="filter.type === 'assetName'">
				<n-input-group-label size="small">{{ filter.label }}</n-input-group-label>
				<n-input v-model:value="filter.value" autosize placeholder="Input..." size="small" class="!min-w-40" />
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

		<n-button v-if="filters.length" size="small" secondary type="primary" @click="submit()">Submit</n-button>

		<n-button v-if="filters.length" size="small" quaternary @click="reset()">Reset</n-button>
	</div>
</template>

<script setup lang="ts">
import type { AlertsFilterTypes } from "@/api/endpoints/incidentManagement"
import type { Customer } from "@/types/customers.d"
import type { AlertStatus } from "@/types/incidentManagement/alerts.d"
import type { SourceName } from "@/types/incidentManagement/sources.d"
import type { AlertsListFilter } from "./types.d"
import Api from "@/api"
import Icon from "@/components/common/Icon.vue"
import _castArray from "lodash/castArray"
import _cloneDeep from "lodash/cloneDeep"
import _orderBy from "lodash/orderBy"
import { NButton, NDropdown, NInput, NInputGroup, NInputGroupLabel, NSelect, useMessage } from "naive-ui"
import { computed, inject, onBeforeMount, ref, type Ref } from "vue"
import { useRoute, useRouter } from "vue-router"

const { useQueryString } = defineProps<{ useQueryString?: boolean }>()

const emit = defineEmits<{
	(e: "submit", value: AlertsListFilter[]): void
}>()

const AddIcon = "carbon:add"
const DelIcon = "carbon:delete"
const router = useRouter()
const route = useRoute()
const message = useMessage()
const loadingAvailableUsers = ref(false)
const loadingConfiguredSources = ref(false)
const loadingCustomers = ref(false)
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
	filters.value.push({ type: key, value: null, label: typeOptions.find(o => o.value === key)?.label || key })
}

function delFilter(key: AlertsFilterTypes) {
	filters.value = filters.value.filter(o => o.type !== key)
}

function reset() {
	filters.value = []
	submit()
}

function submit() {
	emit("submit", filters.value)
	setQueryString()
}

function setQueryString() {
	if (useQueryString) {
		router.replace({
			query: filters.value.reduce(
				(acc, curr) => {
					if (curr.value) {
						acc[curr.type] = curr.value
					}
					return acc
				},
				{} as { [key: string]: string }
			)
		})
	}
}

function getQueryString() {
	if (useQueryString) {
		filters.value = Object.entries(route.query)
			.filter(o => !!o[0] && !!o[1])
			.map(o => ({
				type: o[0],
				label: typeOptions.find(t => t.value === o[0])?.label || o[0],
				value: o[1]
			}))
	}
}

function getAvailableUsers() {
	loadingAvailableUsers.value = true

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
		.finally(() => {
			loadingAvailableUsers.value = false
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

function getConfiguredSources() {
	loadingConfiguredSources.value = true

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
		.finally(() => {
			loadingConfiguredSources.value = false
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

onBeforeMount(() => {
	getQueryString()
	if (useQueryString && filters.value.length) {
		submit()
	}
})
</script>
