<template>
	<n-spin :show="loading">
		<template v-if="resolvedEvent">
			<CardEntity :embedded>
				<template #headerMain>
					<span class="font-mono text-sm">#{{ displayId }}</span>
				</template>
				<template v-if="formattedTimestamp" #headerExtra>
					{{ formattedTimestamp }}
				</template>

				<template #mainExtra>
					<div class="flex flex-wrap gap-2">
						<Badge v-if="customerCode" type="splitted" bright size="small">
							<template #label>Customer</template>
							<template #value>{{ customerCode }}</template>
						</Badge>
						<Badge v-if="sourceName" type="splitted" bright size="small">
							<template #label>Source</template>
							<template #value>{{ sourceName }}</template>
						</Badge>
						<Badge v-if="resolvedEvent._index" type="splitted" bright size="small">
							<template #label>Index</template>
							<template #value>{{ resolvedEvent._index }}</template>
						</Badge>
						<Badge v-if="ruleLevel != null" type="splitted" bright size="small" :color="ruleLevelColor">
							<template #label>Level</template>
							<template #value>{{ ruleLevel }}</template>
						</Badge>
					</div>
				</template>

				<EventDetail :event="resolvedEvent" @filter-add="onFilterAdd" @filter-exclude="onFilterExclude" />
			</CardEntity>
		</template>

		<n-empty v-else-if="!loading" description="Event not found" class="h-48 justify-center" />
	</n-spin>
</template>

<script setup lang="ts">
import type { ApiError } from "@/types/common"
import type { EventSearchResult } from "@/types/events"
import axios from "axios"
import { NEmpty, NSpin, useMessage } from "naive-ui"
import { computed, ref, watch } from "vue"
import Api from "@/api"
import Badge from "@/components/common/Badge.vue"
import CardEntity from "@/components/common/cards/CardEntity.vue"
import { useNavigation } from "@/composables/useNavigation"
import { useSettingsStore } from "@/stores/settings"
import { getApiErrorMessage } from "@/utils"
import { formatDate } from "@/utils/format"
import EventDetail from "./EventDetail.vue"

const props = withDefaults(
	defineProps<{
		event?: EventSearchResult | null
		customerCode?: string | null
		sourceName?: string | null
		indexName?: string | null
		eventId?: string | null
		embedded?: boolean
	}>(),
	{ embedded: false }
)

const emit = defineEmits<{
	loaded: [event: EventSearchResult]
}>()

const message = useMessage()
const dFormats = useSettingsStore().dateFormat
const { routeEventSearch } = useNavigation()

const loading = ref(false)
const fetchedEvent = ref<EventSearchResult | null>(null)

let abortController: AbortController | null = null

const resolvedEvent = computed(() => props.event ?? fetchedEvent.value)

const displayId = computed(() => resolvedEvent.value?._id || resolvedEvent.value?.id || "—")

const formattedTimestamp = computed(() => {
	const ts = resolvedEvent.value?.timestamp || resolvedEvent.value?.["@timestamp"]
	if (!ts) return ""
	return String(formatDate(`${ts}`, dFormats.datetime, { tz: true }))
})

const ruleLevel = computed(() => {
	const level = resolvedEvent.value?.rule_level
	if (level === undefined || level === null || level === "") return null
	const parsed = Number(level)
	return Number.isFinite(parsed) ? parsed : null
})

const ruleLevelColor = computed(() => {
	const level = ruleLevel.value
	if (level == null) return undefined
	if (level >= 12) return "danger"
	if (level >= 8) return "warning"
	if (level >= 4) return "primary"
	return undefined
})

function loadEvent() {
	const customerCode = props.customerCode
	const sourceName = props.sourceName
	const indexName = props.indexName
	const eventId = props.eventId

	if (props.event || !customerCode || !sourceName || !indexName || !eventId) return

	abortController?.abort()
	abortController = new AbortController()
	loading.value = true

	Api.siem
		.getEvent(customerCode, sourceName, { index_name: indexName, event_id: eventId }, abortController.signal)
		.then(res => {
			loading.value = false

			if (res.data.success && res.data.event) {
				fetchedEvent.value = res.data.event
				emit("loaded", res.data.event)
			} else {
				message.warning(res.data?.message || "Event not found.")
			}
		})
		.catch(err => {
			if (!axios.isCancel(err)) {
				message.error(getApiErrorMessage(err as ApiError) || "Failed to load event.")
				loading.value = false
			}
		})
}

function buildSearchQuery(field: string, value: string, exclude = false) {
	return exclude ? `NOT ${field}:"${value}"` : `${field}:"${value}"`
}

function onFilterAdd(field: string, value: string) {
	if (!props.customerCode || !props.sourceName) return
	routeEventSearch({
		customer_code: props.customerCode,
		source_name: props.sourceName,
		query: buildSearchQuery(field, value)
	}).navigate()
}

function onFilterExclude(field: string, value: string) {
	if (!props.customerCode || !props.sourceName) return
	routeEventSearch({
		customer_code: props.customerCode,
		source_name: props.sourceName,
		query: buildSearchQuery(field, value, true)
	}).navigate()
}

watch(
	() => [props.event, props.customerCode, props.sourceName, props.indexName, props.eventId] as const,
	([event]) => {
		if (event) {
			abortController?.abort()
			fetchedEvent.value = null
			loading.value = false
			emit("loaded", event)
			return
		}

		loadEvent()
	},
	{ immediate: true }
)

defineExpose({ loading, resolvedEvent })
</script>
