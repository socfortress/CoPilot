<template>
	<div class="mb-4 flex flex-wrap gap-3">
		<div v-for="filter of filters" :key="filter.type">
			<n-input-group v-if="filter.type === 'customer_code'">
				<n-input-group-label size="small" class="flex! items-center gap-2">
					<Icon :name="CustomersIcon" />
					{{ getFilterLabel(filter.type) }}
				</n-input-group-label>
				<n-select
					:value="stringFilterValue(filter)"
					size="small"
					:options="customerOptions"
					placeholder="Select..."
					clearable
					filterable
					:loading="loadingCustomers"
					class="w-50!"
					:consistent-menu-width="false"
					@update:value="updateStringFilterValue(filter, $event)"
				/>
				<n-button size="small" secondary tabindex="-1" @click="delFilter(filter.type)">
					<template #icon>
						<Icon :name="DelIcon" />
					</template>
				</n-button>
			</n-input-group>

			<n-input-group
				v-if="filter.type === 'agent_name' && (typeof filter.value === 'string' || filter.value === null)"
			>
				<n-input-group-label size="small" class="flex! items-center gap-2">
					<Icon :name="AgentsIcon" />
					{{ getFilterLabel(filter.type) }}
				</n-input-group-label>
				<n-input
					:value="stringFilterValue(filter)"
					autosize
					placeholder="Input..."
					size="small"
					class="min-w-60!"
					@update:value="updateStringFilterValue(filter, $event)"
				/>
				<n-button size="small" secondary tabindex="-1" @click="delFilter(filter.type)">
					<template #icon>
						<Icon :name="DelIcon" />
					</template>
				</n-button>
			</n-input-group>

			<n-input-group
				v-if="filter.type === 'policy_name' && (typeof filter.value === 'string' || filter.value === null)"
			>
				<n-input-group-label size="small" class="flex! items-center gap-2">
					<Icon :name="PolicyIcon" />
					{{ getFilterLabel(filter.type) }}
				</n-input-group-label>
				<n-input
					:value="stringFilterValue(filter)"
					autosize
					placeholder="Input..."
					size="small"
					class="min-w-60!"
					@update:value="updateStringFilterValue(filter, $event)"
				/>
				<n-button size="small" secondary tabindex="-1" @click="delFilter(filter.type)">
					<template #icon>
						<Icon :name="DelIcon" />
					</template>
				</n-button>
			</n-input-group>

			<n-input-group v-if="filter.type === 'min_score'">
				<n-input-group-label size="small" class="flex! items-center gap-2">
					<Icon :name="ScoreIcon" />
					{{ getFilterLabel(filter.type) }}
				</n-input-group-label>
				<n-input-number
					:value="numberFilterValue(filter)"
					size="small"
					placeholder="0"
					:min="0"
					:max="100"
					clearable
					class="w-24!"
					@update:value="updateNumberFilterValue(filter, $event)"
				/>
				<n-button size="small" secondary tabindex="-1" @click="delFilter(filter.type)">
					<template #icon>
						<Icon :name="DelIcon" />
					</template>
				</n-button>
			</n-input-group>

			<n-input-group v-if="filter.type === 'max_score'">
				<n-input-group-label size="small" class="flex! items-center gap-2">
					<Icon :name="ScoreIcon" />
					{{ getFilterLabel(filter.type) }}
				</n-input-group-label>
				<n-input-number
					:value="numberFilterValue(filter)"
					size="small"
					placeholder="100"
					:min="0"
					:max="100"
					clearable
					class="w-24!"
					@update:value="updateNumberFilterValue(filter, $event)"
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
			<n-button size="small" dashed @click="loadCustomers()">
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
import type { ScaStreamingFilterType, ScaStreamingListFilter } from "./types.d"
import type { Customer } from "@/types/customers.d"
import _cloneDeep from "lodash/cloneDeep"
import _isEqual from "lodash/isEqual"
import {
	NButton,
	NDropdown,
	NInput,
	NInputGroup,
	NInputGroupLabel,
	NInputNumber,
	NSelect,
	useMessage
} from "naive-ui"
import { computed, onMounted, ref } from "vue"
import Api from "@/api"
import Icon from "@/components/common/Icon.vue"

const emit = defineEmits<{
	(e: "submit", value: ScaStreamingListFilter[]): void
	(
		e: "mounted",
		value: {
			setFilter: (payload: ScaStreamingListFilter[]) => void
		}
	): void
}>()

const AgentsIcon = "carbon:network-3"
const PolicyIcon = "carbon:document"
const CustomersIcon = "carbon:user-multiple"
const ScoreIcon = "carbon:chart-line"
const AddIcon = "carbon:add"
const DelIcon = "carbon:delete"

const message = useMessage()
const loadingCustomers = ref(false)
const customersList = ref<Customer[]>([])

const typeOptions: { label: string; value: ScaStreamingFilterType }[] = [
	{ label: "Customer", value: "customer_code" },
	{ label: "Agent", value: "agent_name" },
	{ label: "Policy", value: "policy_name" },
	{ label: "Min Score", value: "min_score" },
	{ label: "Max Score", value: "max_score" }
]

const filters = ref<ScaStreamingListFilter[]>([])
const lastFilters = ref<ScaStreamingListFilter[]>([])

const customerOptions = computed(() =>
	customersList.value.map(customer => ({
		label: `#${customer.customer_code} - ${customer.customer_name}`,
		value: customer.customer_code
	}))
)

const availableFilters = computed(() =>
	typeOptions
		.filter(option => !filters.value.some(filter => filter.type === option.value))
		.map(option => ({ key: option.value, label: option.label }))
)

const isDirty = computed(() => !_isEqual(filters.value, lastFilters.value))

function getFilterLabel(type: ScaStreamingFilterType): string {
	return typeOptions.find(option => option.value === type)?.label || type
}

function stringFilterValue(filter: ScaStreamingListFilter): string | null {
	return typeof filter.value === "string" ? filter.value : null
}

function updateStringFilterValue(filter: ScaStreamingListFilter, value: string | null) {
	filter.value = value
}

function numberFilterValue(filter: ScaStreamingListFilter): number | null {
	return typeof filter.value === "number" ? filter.value : null
}

function updateNumberFilterValue(filter: ScaStreamingListFilter, value: number | null) {
	filter.value = value
}

function defaultValueForType(type: ScaStreamingFilterType): string | number | null {
	if (type === "min_score" || type === "max_score") return null
	return ""
}

function addFilter(key: ScaStreamingFilterType) {
	if (key === "customer_code" && !customersList.value.length) {
		loadCustomers()
	}

	filters.value.push({ type: key, value: defaultValueForType(key) })
}

function delFilter(key: ScaStreamingFilterType) {
	filters.value = filters.value.filter(filter => filter.type !== key)
	submit()
}

function setFilter(newFilters: ScaStreamingListFilter[]) {
	for (const newFilter of newFilters) {
		const filterIndex = filters.value.findIndex(filter => filter.type === newFilter.type)

		if (filterIndex !== -1) {
			if (newFilter.value !== null && newFilter.value !== "" && filters.value[filterIndex]) {
				filters.value[filterIndex].value = newFilter.value
			} else {
				delFilter(newFilter.type)
			}
		} else if (newFilter.value !== null && newFilter.value !== "") {
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

function loadCustomers() {
	if (loadingCustomers.value || customersList.value.length) return

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

onMounted(() => {
	emit("mounted", {
		setFilter
	})
})
</script>
