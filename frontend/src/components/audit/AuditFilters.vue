<template>
	<div class="audit-filters flex flex-wrap gap-3">
		<div v-for="filter of filters" :key="filter.type">
			<n-input-group v-if="filter.type === 'action'">
				<n-input-group-label size="small">{{ getFilterLabel(filter.type) }}</n-input-group-label>
				<n-select
					v-model:value="filter.value"
					size="small"
					:options="actionOptions"
					placeholder="Select..."
					filterable
					class="min-w-48!"
					:loading="loadingVocabularies || !actionOptions.length"
				/>
				<n-button size="small" secondary tabindex="-1" @click="delFilter(filter.type)">
					<template #icon>
						<Icon :name="DelIcon" />
					</template>
				</n-button>
			</n-input-group>

			<n-input-group v-if="filter.type === 'result'">
				<n-input-group-label size="small">{{ getFilterLabel(filter.type) }}</n-input-group-label>
				<n-select
					v-model:value="filter.value"
					size="small"
					:options="resultOptions"
					placeholder="Select..."
					class="w-32!"
					:loading="loadingVocabularies || !resultOptions.length"
				/>
				<n-button size="small" secondary tabindex="-1" @click="delFilter(filter.type)">
					<template #icon>
						<Icon :name="DelIcon" />
					</template>
				</n-button>
			</n-input-group>

			<n-input-group
				v-if="filter.type === 'actor_username' && (typeof filter.value === 'string' || filter.value === null)"
			>
				<n-input-group-label size="small">{{ getFilterLabel(filter.type) }}</n-input-group-label>
				<n-input v-model:value="filter.value" autosize placeholder="Input..." size="small" class="min-w-40!" />
				<n-button size="small" secondary tabindex="-1" @click="delFilter(filter.type)">
					<template #icon>
						<Icon :name="DelIcon" />
					</template>
				</n-button>
			</n-input-group>

			<n-input-group
				v-if="filter.type === 'entity_type' && (typeof filter.value === 'string' || filter.value === null)"
			>
				<n-input-group-label size="small">{{ getFilterLabel(filter.type) }}</n-input-group-label>
				<n-input
					v-model:value="filter.value"
					autosize
					placeholder="e.g. agent, user"
					size="small"
					class="min-w-40!"
				/>
				<n-button size="small" secondary tabindex="-1" @click="delFilter(filter.type)">
					<template #icon>
						<Icon :name="DelIcon" />
					</template>
				</n-button>
			</n-input-group>

			<n-input-group v-if="filter.type === 'customer_code'">
				<n-input-group-label size="small">{{ getFilterLabel(filter.type) }}</n-input-group-label>
				<n-select
					:value="customerFilterValue(filter)"
					:options="customersOptions"
					placeholder="Select..."
					size="small"
					multiple
					filterable
					clearable
					class="min-w-56!"
					:max-tag-count="2"
					:consistent-menu-width="false"
					:loading="loadingCustomers"
					@update:value="filter.value = $event"
				/>
				<n-button size="small" secondary tabindex="-1" @click="delFilter(filter.type)">
					<template #icon>
						<Icon :name="DelIcon" />
					</template>
				</n-button>
			</n-input-group>

			<n-input-group
				v-if="filter.type === 'search' && (typeof filter.value === 'string' || filter.value === null)"
			>
				<n-input-group-label size="small">{{ getFilterLabel(filter.type) }}</n-input-group-label>
				<n-input
					v-model:value="filter.value"
					autosize
					placeholder="Details / username / entity"
					size="small"
					class="min-w-48!"
				/>
				<n-button size="small" secondary tabindex="-1" @click="delFilter(filter.type)">
					<template #icon>
						<Icon :name="DelIcon" />
					</template>
				</n-button>
			</n-input-group>

			<n-input-group v-if="filter.type === 'dateRange'">
				<n-input-group-label size="small">{{ getFilterLabel(filter.type) }}</n-input-group-label>
				<n-date-picker
					:value="dateRangeValue(filter)"
					type="datetimerange"
					size="small"
					clearable
					class="min-w-72!"
					@update:value="setDateRangeValue(filter, $event)"
				/>
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
import type { AuditFilterTypes, AuditListFilter, AuditListFilterValue } from "./types"
import type { ApiError } from "@/types/common"
import type { Customer } from "@/types/customers"
import _cloneDeep from "lodash/cloneDeep"
import _isEqual from "lodash/isEqual"
import { NButton, NDatePicker, NDropdown, NInput, NInputGroup, NInputGroupLabel, NSelect, useMessage } from "naive-ui"
import { computed, onBeforeMount, ref } from "vue"
import { useRoute, useRouter } from "vue-router"
import Api from "@/api"
import Icon from "@/components/common/Icon.vue"
import { useGlobalCustomerFilter } from "@/composables/useGlobalCustomerFilter"
import { getApiErrorMessage } from "@/utils"

const { useQueryString, preset } = defineProps<{ useQueryString?: boolean; preset?: AuditListFilter[] }>()

const emit = defineEmits<{
	(e: "submit", value: AuditListFilter[]): void
}>()

const AddIcon = "carbon:add"
const DelIcon = "carbon:delete"

const router = useRouter()
const route = useRoute()
const message = useMessage()
const { globalCustomerCodes, onGlobalCustomerFilterChange } = useGlobalCustomerFilter()

const loadingVocabularies = ref(false)
const loadingCustomers = ref(false)
const customersList = ref<Customer[]>([])
const actionsList = ref<string[]>([])
const resultsList = ref<string[]>([])

const customersOptions = computed(() =>
	customersList.value.map(o => ({ label: `#${o.customer_code} - ${o.customer_name}`, value: o.customer_code }))
)
const actionOptions = computed(() => actionsList.value.map(a => ({ label: a, value: a })))
const resultOptions = computed(() => resultsList.value.map(r => ({ label: r, value: r })))

const typeOptions: { label: string; value: AuditFilterTypes }[] = [
	{ label: "Action", value: "action" },
	{ label: "Result", value: "result" },
	{ label: "Actor", value: "actor_username" },
	{ label: "Entity type", value: "entity_type" },
	{ label: "Customer", value: "customer_code" },
	{ label: "Search", value: "search" },
	{ label: "Date range", value: "dateRange" }
]

const filters = ref<AuditListFilter[]>([])
const lastFilters = ref<AuditListFilter[]>([])

const availableFilters = computed(() =>
	typeOptions
		.filter(o => !filters.value.map(f => f.type).includes(o.value))
		.map(t => ({ key: t.value, label: t.label }))
)

const isDirty = computed(() => !_isEqual(filters.value, lastFilters.value))

function getFilterLabel(type: AuditFilterTypes): string {
	return typeOptions.find(o => o.value === type)?.label || type
}

/** The customer filter is multi-valued; anything else stored there is treated as empty. */
function customerFilterValue(filter: AuditListFilter): string[] {
	return Array.isArray(filter.value) && filter.value.every(v => typeof v === "string")
		? (filter.value as string[])
		: []
}

function dateRangeValue(filter: AuditListFilter): [number, number] | null {
	// Array values are now either a date range or the customer_code list — check the shape,
	// not just Array.isArray.
	if (filter.type !== "dateRange" || !Array.isArray(filter.value)) return null

	const [from, to] = filter.value
	return typeof from === "number" && typeof to === "number" ? [from, to] : null
}

function setDateRangeValue(filter: AuditListFilter, value: [number, number] | null) {
	filter.value = value
}

function isKnownFilterType(type: string): type is AuditFilterTypes {
	return typeOptions.some(o => o.value === type)
}

function parseQueryValue(type: AuditFilterTypes, raw: string | string[]): AuditListFilterValue {
	if (type === "dateRange") {
		const value = Array.isArray(raw) ? raw[0] : raw
		if (!value) return null

		const parts = value.split(",").map(Number)
		if (parts.length === 2 && parts.every(n => !Number.isNaN(n))) {
			return parts as [number, number]
		}
		return null
	}

	if (type === "customer_code") {
		// Repeated params arrive as an array, a lone one as a string — normalize to an array.
		const codes = (Array.isArray(raw) ? raw : [raw]).filter(Boolean)
		return codes.length ? codes : null
	}

	return (Array.isArray(raw) ? raw[0] : raw) || null
}

function addFilter(key: AuditFilterTypes) {
	filters.value.push({ type: key, value: null })
}

function delFilter(key: AuditFilterTypes) {
	filters.value = filters.value.filter(o => o.type !== key)
	submit()
}

function setFilter(newFilters: AuditListFilter[]) {
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
	setQueryString()
}

function setQueryString() {
	if (!useQueryString) return

	const query = filters.value
		.filter(filter => filter.value)
		.filter(filter => !Array.isArray(filter.value) || filter.value.length)
		.reduce<Record<string, string | string[]>>((acc, filter) => {
			if (filter.type === "dateRange" && Array.isArray(filter.value)) {
				acc[filter.type] = filter.value.join(",")
			} else {
				acc[filter.type] = filter.value as string | string[]
			}
			return acc
		}, {})

	router.replace({ query })
}

function getQueryString() {
	if (!useQueryString) return

	filters.value = Object.entries(route.query)
		.filter((entry): entry is [AuditFilterTypes, string | string[]] => isKnownFilterType(entry[0]) && !!entry[1])
		.map(([type, value]) => ({
			type,
			value: parseQueryValue(type, value)
		}))
		.filter(filter => filter.value !== null)
}

function getCustomers() {
	loadingCustomers.value = true

	Api.customers
		.getCustomers({})
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
			loadingCustomers.value = false
		})
}

function getVocabularies() {
	loadingVocabularies.value = true

	Api.audit
		.getAuditVocabularies()
		.then(res => {
			if (res.data.success) {
				actionsList.value = res.data.actions || []
				resultsList.value = res.data.results || []
			}
		})
		.catch(err => {
			message.error(getApiErrorMessage(err as ApiError) || "Failed to load audit filter options")
		})
		.finally(() => {
			loadingVocabularies.value = false
		})
}

function load() {
	if (!actionsList.value.length || !resultsList.value.length) {
		getVocabularies()
	}
	if (!customersList.value.length) {
		getCustomers()
	}
}

function applyGlobalCustomerCodeFilter() {
	if (filters.value.some(f => f.type === "customer_code" && f.value)) {
		return false
	}
	const codes = globalCustomerCodes.value
	if (!codes.length) {
		return false
	}
	filters.value.push({ type: "customer_code", value: [...codes] })
	return true
}

onBeforeMount(() => {
	if (preset?.length) {
		filters.value = preset
	} else {
		getQueryString()
		applyGlobalCustomerCodeFilter()
	}

	if (filters.value.length) {
		load()
		submit()
	}
})

// A preset locks the list to a fixed scope (embedded usages) — never live-sync those.
// setFilter() already upserts-or-deletes and submits, so a null value clears the filter.
if (!preset?.length) {
	onGlobalCustomerFilterChange(codes =>
		setFilter([{ type: "customer_code", value: codes.length ? [...codes] : null }])
	)
}

defineExpose({ setFilter })
</script>
