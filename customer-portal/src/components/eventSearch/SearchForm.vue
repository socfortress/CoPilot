<template>
	<div class="@container w-full">
		<div class="grid grid-cols-1 gap-6 @md:grid-cols-2 @5xl:grid-cols-3">
			<n-form-item label="Customer" :show-feedback="false">
				<n-input v-model:value="selectedCustomerCode" disabled />
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
					:loading
					:disabled="!selectedCustomerCode || !selectedSourceName"
					@click="searchEvents"
				>
					<template #icon>
						<Icon name="carbon:search" />
					</template>
					Search
				</n-button>

				<n-select v-model:value="pageSize" :options="pageSizeOptions" class="w-36!" />
			</div>
		</div>
	</div>
</template>

<script setup lang="ts">
import type { MentionOption } from "naive-ui"
import type { VNodeChild } from "vue"
import type { ApiError } from "@/types/common"
import type { EventSearchQueryTimerange, EventSourceItem, FieldMapping } from "@/types/siem"
import {
	NButton,
	NDatePicker,
	NFormItem,
	NInput,
	NInputGroup,
	NInputNumber,
	NMention,
	NSelect,
	NSpin,
	useMessage
} from "naive-ui"
import { computed, h, onBeforeMount, ref, watch } from "vue"
import { useRoute } from "vue-router"
import Api from "@/api"
import Icon from "@/components/common/Icon.vue"
import { useAuthStore } from "@/stores/auth"
import { getApiErrorMessage } from "@/utils"

export interface SearchFormParams {
	customerCode: string
	sourceName: string | null
	query: string
	timerange: EventSearchQueryTimerange
	timeFrom: number | null
	timeTo: number | null
	timeMode: "relative" | "absolute"
	pageSize: number
}

export interface SearchFormLoad {
	customerCode: string
	eventSources: EventSourceItem[]
}

defineProps<{
	loading: boolean
}>()

const emit = defineEmits<{
	(e: "search", value: SearchFormParams): void
	(e: "loaded", value: SearchFormLoad): void
}>()

const query = defineModel<string>("query")

const TRAILING_WHITESPACE_RE = /\s$/

const route = useRoute()
const authStore = useAuthStore()
const message = useMessage()

const customerCode = computed(() => authStore.userCustomerCode)
const selectedCustomerCode = ref(customerCode.value || "")

const eventSources = ref<EventSourceItem[]>([])
const loadingEventSources = ref(false)
const selectedSourceName = ref<string | null>(null)
const enabledSources = computed(() => eventSources.value.filter(s => s.enabled))
const eventSourceOptions = computed(() =>
	enabledSources.value.map(s => ({ label: `${s.name} (${s.event_type})`, value: s.name }))
)

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
const daterange = ref<[number, number]>([1183135260000, Date.now()])
const timerangeMode = ref<"relative" | "absolute">("relative")

const pageSizeOptions = [
	{ label: "25 per page", value: 25 },
	{ label: "50 per page", value: 50 },
	{ label: "100 per page", value: 100 },
	{ label: "250 per page", value: 250 }
]
const pageSize = ref(pageSizeOptions[1].value)

const loadingFieldMappings = ref(false)
const fieldMappings = ref<FieldMapping[]>([])
const suggestionOptions = computed(() => {
	return fieldMappings.value.map(f => ({ label: f.field, type: f.type, value: f.field }))
})

function renderLabel(option: MentionOption): VNodeChild {
	const label = String(option.label ?? "")
	const type = String(option.type ?? "")

	return h("div", { class: "flex items-center gap-2 justify-between w-full" }, [
		h("div", { class: "text-sm font-medium" }, label),
		h("div", { class: "text-xs text-secondary" }, type)
	])
}

async function loadEventSources(customerCode: string) {
	loadingEventSources.value = true
	eventSources.value = []
	selectedSourceName.value = null
	fieldMappings.value = []

	try {
		const response = await Api.siem.getEventSources(customerCode)
		eventSources.value = response.data.event_sources
	} catch (err) {
		message.error(getApiErrorMessage(err as ApiError) || "Failed to load event sources")
	} finally {
		loadingEventSources.value = false

		emit("loaded", {
			customerCode,
			eventSources: eventSources.value
		})
	}
}

async function loadFieldMappings() {
	if (!selectedCustomerCode.value || !selectedSourceName.value) return

	loadingFieldMappings.value = true
	fieldMappings.value = []
	try {
		const response = await Api.siem.getFieldMappings(selectedCustomerCode.value, selectedSourceName.value)
		fieldMappings.value = response.data.fields
	} catch {
		fieldMappings.value = []
	} finally {
		loadingFieldMappings.value = false
	}
}

async function searchEvents() {
	if (!selectedCustomerCode.value || !selectedSourceName.value) return

	emit("search", {
		customerCode: selectedCustomerCode.value,
		sourceName: selectedSourceName.value,
		query: query.value || "",
		timerange: timerange.value,
		timeFrom: timerangeMode.value === "absolute" ? daterange.value[0] : null,
		timeTo: timerangeMode.value === "absolute" ? daterange.value[1] : null,
		timeMode: timerangeMode.value,
		pageSize: pageSize.value
	})
}

function onMentionSelect(option: MentionOption, prefix: string) {
	// Current query text and the raw token as typed in the mention (e.g. "#field")
	const currentQuery = query.value || ""
	const target = `${prefix}${option.value}`

	// Find the last occurrence of the typed token to replace it
	const lastIndex = currentQuery.lastIndexOf(target)

	if (lastIndex === -1) {
		// If only the trigger is present (e.g. "... #"), replace the last trigger with "field:"
		const lastPrefixIndex = currentQuery.lastIndexOf(prefix)
		if (lastPrefixIndex !== -1) {
			const before = currentQuery.slice(0, lastPrefixIndex)
			const after = currentQuery.slice(lastPrefixIndex + prefix.length)
			const needsSpace = before.length > 0 && !TRAILING_WHITESPACE_RE.test(before)
			const replacement = `${needsSpace ? " " : ""}${option.value}:`
			query.value = `${before}${replacement}${after}`
			return
		}

		// If neither token nor trigger is found, append the field followed by ":" at the end of the query
		const needsSpace = currentQuery.length > 0 && !TRAILING_WHITESPACE_RE.test(currentQuery)
		query.value = `${currentQuery}${needsSpace ? " " : ""}${option.value}:`
		return
	}

	// Split query around the matched token
	const before = currentQuery.slice(0, lastIndex)
	const after = currentQuery.slice(lastIndex + target.length)

	// Rebuild query replacing the token with the plain field name followed by ":"
	const needsSpace = before.length > 0 && !TRAILING_WHITESPACE_RE.test(before)
	const replacement = `${needsSpace ? " " : ""}${option.value}:`

	query.value = `${before}${replacement}${after}`
}

// -- Lifecycle --
async function applyRouteParams() {
	const qCustomer = (route.query.customer_code || customerCode.value) as string
	const qSource = route.query.source_name as string | undefined
	const qQuery = route.query.query as string | undefined

	if (!qCustomer) return

	selectedCustomerCode.value = qCustomer
	await loadEventSources(qCustomer)

	if (qSource) {
		const match = enabledSources.value.find(s => s.name === qSource)
		if (match) {
			selectedSourceName.value = match.name
		}
	}

	if (qQuery) {
		query.value = qQuery
	}

	if (selectedCustomerCode.value && selectedSourceName.value) {
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
	applyRouteParams()
})
</script>
