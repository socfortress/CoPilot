<template>
	<div v-if="requests.length" class="flex flex-col gap-2" data-testid="customer-questions-panel">
		<div
			v-for="request of openRequests"
			:key="request.id"
			class="border-warning bg-warning/5 flex flex-col gap-2 rounded-md border px-3 py-2.5"
			data-testid="customer-question"
		>
			<div class="flex flex-wrap items-center justify-between gap-2">
				<div class="flex flex-wrap items-center gap-2 text-sm">
					<Icon name="carbon:help" :size="15" class="text-warning" />
					<span class="font-semibold">Customer question</span>
					<n-tag
						:type="URGENCY_TAG[request.urgency]"
						size="tiny"
						:bordered="false"
						data-testid="customer-question-urgency"
					>
						{{ URGENCY_LABELS[request.urgency] }}
					</n-tag>
					<span class="text-secondary text-xs">
						<bdi>{{ request.requested_by }}</bdi>
						· {{ formatDate(request.requested_at, dFormats.datetime, { tz: true }) }}
					</span>
				</div>
				<n-button
					size="tiny"
					secondary
					:loading="marking === request.id"
					data-testid="customer-question-answered"
					@click="markAnswered(request)"
				>
					Mark answered
				</n-button>
			</div>
			<p class="text-default m-0 text-sm whitespace-pre-wrap" data-testid="customer-question-text">
				<bdi>{{ request.question }}</bdi>
			</p>
			<p class="text-secondary m-0 text-xs">
				A comment from the SOC here answers it; mark it answered when the reply went another way.
			</p>
		</div>
		<div v-if="answeredCount" class="text-secondary text-xs" data-testid="customer-questions-answered">
			{{ answeredCount }} earlier {{ answeredCount === 1 ? "question" : "questions" }} answered
		</div>
	</div>
</template>

<script setup lang="ts">
import type { QuestionEntity } from "./customerQuestions"
import type { ApiError } from "@/types/common"
import type { SocRequest } from "@/types/soc-requests"
import { NButton, NTag, useMessage } from "naive-ui"
import { computed, onBeforeMount, ref, watch } from "vue"
import Api from "@/api"
import Icon from "@/components/common/Icon.vue"
import { useOpenCustomerQuestions } from "@/composables/useOpenCustomerQuestions"
import { useSettingsStore } from "@/stores/settings"
import { getApiErrorMessage } from "@/utils"
import { formatDate } from "@/utils/format"
import { URGENCY_LABELS, URGENCY_TAG } from "./customerQuestions"

/**
 * The customer's questions on a case or alert (#1305), on its overview: the open ones with what was
 * asked and "Mark answered"; the answered ones counted. Shows nothing when there are none, or when
 * they can't be read. `refreshKey` reloads it (a comment may have just answered one).
 */
const { entity, entityId, refreshKey } = defineProps<{
	entity: QuestionEntity
	entityId: number
	refreshKey?: string | number
}>()

const message = useMessage()
const dFormats = useSettingsStore().dateFormat
const { invalidate } = useOpenCustomerQuestions()

const requests = ref<SocRequest[]>([])
const marking = ref<number | null>(null)

// A question asked from an alert but filed on its case belongs to the case's panel.
const mine = computed(() =>
	requests.value.filter(r => (entity === "case" ? r.case_id === entityId : r.alert_id === entityId))
)
const openRequests = computed(() => mine.value.filter(r => r.status === "open"))
const answeredCount = computed(() => mine.value.length - openRequests.value.length)

async function load() {
	try {
		const res = await Api.socRequests.list(entity === "case" ? { caseId: entityId } : { alertId: entityId })
		requests.value = res.data.requests ?? []
	} catch {
		requests.value = []
	}
}

async function markAnswered(request: SocRequest) {
	marking.value = request.id
	try {
		const res = await Api.socRequests.markAnswered(request.id)
		requests.value = requests.value.map(r => (r.id === request.id ? res.data.request : r))
		message.success("Question marked answered")
		invalidate()
	} catch (err) {
		message.error(getApiErrorMessage(err as ApiError) || "Could not mark the question answered.")
	} finally {
		marking.value = null
	}
}

watch(
	() => [entityId, refreshKey],
	() => {
		load()
	}
)

onBeforeMount(() => {
	load()
})
</script>
