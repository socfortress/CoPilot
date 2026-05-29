<template>
	<div class="flex flex-col gap-4">
		<n-alert v-if="showNoSourcesWarning" title="No Event Sources Configured" type="warning" closable>
			An Event Source needs to be defined for this customer before events can be searched. Go to the customer's
			<strong>Event Sources</strong>
			tab to configure one.
		</n-alert>

		<div class="@container w-full">
			<div class="grid grid-cols-1 gap-6 @md:grid-cols-2 @5xl:grid-cols-3">
				<n-form-item label="Customer" :show-feedback="false">
					<n-select
						v-model:value="selectedCustomerCode"
						placeholder="Select Customer"
						filterable
						:options="customersOptions"
						:loading="loadingCustomers"
						@update:value="onCustomerChange"
					/>
				</n-form-item>

				<n-form-item label="Event Source" :show-feedback="false">
					<n-select
						v-model:value="selectedSourceName"
						placeholder="Select Source"
						filterable
						:options="eventSourceOptions"
						:disabled="!selectedCustomerCode"
						:loading="loadingEventSources"
					/>
				</n-form-item>

				<n-form-item label="Time Range" :show-feedback="false" class="col-span-full @5xl:col-span-1">
					<n-input-group class="w-full">
						<n-input-number
							v-if="timerangeMode === 'relative'"
							v-model:value="filterTimeRange.time"
							:min="1"
							placeholder="Time"
							class="grow text-right [&_input]:pr-3!"
						/>
						<n-select
							v-if="timerangeMode === 'relative'"
							v-model:value="filterTimeRange.unit"
							:options="unitOptions"
							placeholder="Time unit"
							class="w-40!"
						/>
						<n-date-picker
							v-if="timerangeMode === 'absolute'"
							v-model:value="daterange"
							type="datetimerange"
							clearable
							class="grow"
						/>
						<n-button v-if="timerangeMode === 'relative'" secondary @click="timerangeMode = 'absolute'">
							<template #icon>
								<Icon name="carbon:calendar" />
							</template>
						</n-button>
						<n-button v-if="timerangeMode === 'absolute'" secondary @click="timerangeMode = 'relative'">
							<template #icon>
								<Icon name="carbon:reset" />
							</template>
						</n-button>
					</n-input-group>
				</n-form-item>

				<n-form-item label="Lucene Query" :show-feedback="false" class="col-span-full">
					<div class="flex w-full flex-col gap-1">
						<n-mention
							v-model:value="query"
							type="textarea"
							separator=" "
							:autosize="{ minRows: 3, maxRows: 8 }"
							placeholder="e.g. agent_name:web-server AND rule_level:>=10"
							:options="suggestionOptions"
							:prefix="['#']"
							:loading="loadingFieldMappings"
							:render-label
							@select="onMentionSelect"
						>
							<template #empty>
								<n-spin :show="loadingFieldMappings">
									<div class="text-secondary text-xs">No field mappings found</div>
								</n-spin>
							</template>
						</n-mention>
						<p class="text-secondary text-xs">type # to autocomplete</p>
					</div>
				</n-form-item>

				<div class="col-span-full -mt-4 flex items-center justify-end gap-3">
					<n-button
						secondary
						type="primary"
						:loading="loadingEvents"
						:disabled="!selectedCustomerCode || !selectedSourceName"
						@click="searchEvents"
					>
						<template #icon>
							<Icon :name="SearchIcon" />
						</template>
						Search
					</n-button>

					<n-select v-model:value="pageSize" :options="pageSizeOptions" class="w-36!" />
				</div>
			</div>
		</div>
	</div>
</template>

<script setup lang="ts">
import type { MentionOption } from "naive-ui"
import type { VNodeChild } from "vue"
import type { Customer } from "@/types/customers.d"
import type { FieldMapping } from "@/types/events.d"
import type { EventSource } from "@/types/eventSources.d"
import { NAlert, NButton, NDatePicker, NFormItem, NInputGroup, NInputNumber, NMention, NSelect, NSpin, useMessage } from "naive-ui"
import { computed, h, onBeforeMount, ref, watch } from "vue"
import { useRoute } from "vue-router"
import Api from "@/api"
import Icon from "@/components/common/Icon.vue"
import dayjs from "@/utils/dayjs"

export type EventSearchQueryTimerange = `${number}${"h" | "d" | "w"}`

export interface EventSearchFiltersParams {
	customerCode: string
	sourceName: string
	query: string
	timerange: EventSearchQueryTimerange
	timeFrom: number | null
	timeTo: number | null
	timeMode: "relative" | "absolute"
	pageSize: number
	fieldMappings: FieldMapping[]
}

export interface EventSearchFiltersLoad {
	customerCode: string
	eventSources: EventSource[]
}

defineProps<{
	loadingEvents: boolean
}>()

const emit = defineEmits<{
	search: [params: EventSearchFiltersParams]
	loaded: [load: EventSearchFiltersLoad]
}>()

const query = defineModel<string>("query", { default: "" })

const TRAILING_WHITESPACE_RE = /\s$/

const route = useRoute()
const message = useMessage()

const SearchIcon = "carbon:search"

const filterTimeRange = ref<{ unit: "h" | "d" | "w"; time: number }>({
	unit: "h",
	time: 24
})
const unitOptions: { label: string; value: "h" | "d" | "w" }[] = [
	{ label: "Hours", value: "h" },
	{ label: "Days", value: "d" },
	{ label: "Weeks", value: "w" }
]
const timerange = computed<EventSearchQueryTimerange>(
	() => `${filterTimeRange.value.time}${filterTimeRange.value.unit}`
)
const daterange = ref<[number, number]>([dayjs().subtract(1, "day").valueOf(), Date.now()])
const timerangeMode = ref<"relative" | "absolute">("relative")

const pageSizeOptions = [
	{ label: "25 per page", value: 25 },
	{ label: "50 per page", value: 50 },
	{ label: "100 per page", value: 100 },
	{ label: "250 per page", value: 250 }
]

const loadingCustomers = ref(false)
const customersList = ref<Customer[]>([])
const loadingEventSources = ref(false)
const eventSources = ref<EventSource[]>([])
const selectedCustomerCode = ref<string | null>(null)
const selectedSourceName = ref<string | null>(null)
const pageSize = ref(pageSizeOptions[1].value)
const loadingFieldMappings = ref(false)
const fieldMappings = ref<FieldMapping[]>([])

const customersOptions = computed(() =>
	customersList.value.map(o => ({ label: `#${o.customer_code} - ${o.customer_name}`, value: o.customer_code }))
)

const eventSourceOptions = computed(() =>
	eventSources.value.filter(s => s.enabled).map(s => ({ label: `${s.name} (${s.event_type})`, value: s.name }))
)

const showNoSourcesWarning = computed(
	() => selectedCustomerCode.value && !loadingEventSources.value && eventSources.value.length === 0
)

const suggestionOptions = computed(() =>
	fieldMappings.value.map(f => ({ label: f.field, type: f.type, value: f.field }))
)

function renderLabel(option: MentionOption): VNodeChild {
	const label = String(option.label ?? "")
	const type = String(option.type ?? "")

	return h("div", { class: "flex w-full items-center justify-between gap-2" }, [
		h("div", { class: "text-sm font-medium font-mono" }, label),
		h("div", { class: "text-secondary text-xs" }, type)
	])
}

function getCustomers() {
	loadingCustomers.value = true
	return Api.customers
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

function getEventSources(customerCode: string) {
	loadingEventSources.value = true
	eventSources.value = []
	selectedSourceName.value = null
	fieldMappings.value = []

	return Api.siem
		.getEventSources(customerCode)
		.then(res => {
			if (res.data.success) {
				eventSources.value = res.data?.event_sources || []
			} else {
				message.warning(res.data?.message || "An error occurred. Please try again later.")
			}
		})
		.catch(err => {
			message.error(err.response?.data?.message || "An error occurred. Please try again later.")
		})
		.finally(() => {
			loadingEventSources.value = false
			emit("loaded", { customerCode, eventSources: eventSources.value })
		})
}

async function loadFieldMappings() {
	if (!selectedCustomerCode.value || !selectedSourceName.value) return

	loadingFieldMappings.value = true
	fieldMappings.value = []

	try {
		const res = await Api.siem.getFieldMappings(selectedCustomerCode.value, selectedSourceName.value)
		if (res.data.success) {
			fieldMappings.value = res.data.fields || []
		}
	} catch {
		fieldMappings.value = []
	} finally {
		loadingFieldMappings.value = false
	}
}

function onCustomerChange(code: string) {
	if (code) {
		getEventSources(code)
	}
}

function searchEvents() {
	if (!selectedCustomerCode.value || !selectedSourceName.value) return

	emit("search", {
		customerCode: selectedCustomerCode.value,
		sourceName: selectedSourceName.value,
		query: query.value || "",
		timerange: timerange.value,
		timeFrom: timerangeMode.value === "absolute" ? daterange.value[0] : null,
		timeTo: timerangeMode.value === "absolute" ? daterange.value[1] : null,
		timeMode: timerangeMode.value,
		pageSize: pageSize.value,
		fieldMappings: fieldMappings.value
	})
}

function onMentionSelect(option: MentionOption, prefix: string) {
	const currentQuery = query.value || ""
	const target = `${prefix}${option.value}`
	const lastIndex = currentQuery.lastIndexOf(target)

	if (lastIndex === -1) {
		const lastPrefixIndex = currentQuery.lastIndexOf(prefix)
		if (lastPrefixIndex !== -1) {
			const before = currentQuery.slice(0, lastPrefixIndex)
			const after = currentQuery.slice(lastPrefixIndex + prefix.length)
			const needsSpace = before.length > 0 && !TRAILING_WHITESPACE_RE.test(before)
			const replacement = `${needsSpace ? " " : ""}${option.value}:`
			query.value = `${before}${replacement}${after}`
			return
		}

		const needsSpace = currentQuery.length > 0 && !TRAILING_WHITESPACE_RE.test(currentQuery)
		query.value = `${currentQuery}${needsSpace ? " " : ""}${option.value}:`
		return
	}

	const before = currentQuery.slice(0, lastIndex)
	const after = currentQuery.slice(lastIndex + target.length)
	const needsSpace = before.length > 0 && !TRAILING_WHITESPACE_RE.test(before)
	const replacement = `${needsSpace ? " " : ""}${option.value}:`

	query.value = `${before}${replacement}${after}`
}

async function applyRouteParams() {
	const qp = route.query
	if (!qp.customer_code) return

	const code = String(qp.customer_code)
	selectedCustomerCode.value = code

	if (qp.query) {
		query.value = String(qp.query)
	}

	await getEventSources(code)

	const targetSource = qp.source_name ? String(qp.source_name) : null
	if (targetSource) {
		const match = eventSources.value.find(s => s.name === targetSource && s.enabled)
		if (match) {
			selectedSourceName.value = match.name
		}
	} else {
		const edr = eventSources.value.find(s => s.event_type === "EDR" && s.enabled)
		if (edr) {
			selectedSourceName.value = edr.name
		}
	}

	if (selectedSourceName.value) {
		await loadFieldMappings()
		searchEvents()
	}
}

watch(
	selectedSourceName,
	val => {
		if (val) {
			loadFieldMappings()
		}
	},
	{ immediate: true }
)

onBeforeMount(() => {
	getCustomers().then(() => applyRouteParams())
})
</script>
