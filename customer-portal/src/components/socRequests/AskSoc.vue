<template>
	<div class="flex flex-col gap-6" data-testid="ask-soc">
		<form class="flex flex-col gap-4" data-testid="ask-soc-form" @submit.prevent="send()">
			<div class="flex flex-col gap-1">
				<h3 class="m-0 text-base font-semibold">Ask the SOC</h3>
				<p class="text-secondary m-0 max-w-prose text-sm">
					Your question goes to the SOC analysts as a comment signed by you on the
					{{ entity === "alert" ? "case or alert you choose" : "case" }}. Their reply appears in the comments.
				</p>
			</div>

			<n-input
				v-model:value="question"
				type="textarea"
				placeholder="What would you like to know?"
				:autosize="{ minRows: 3, maxRows: 10 }"
				:status="touched && problem ? 'error' : undefined"
				:disabled="sending"
				:input-props="{ 'aria-label': 'Your question for the SOC' }"
				data-testid="ask-soc-question"
				@blur="touched = true"
			/>
			<div class="-mt-3 flex flex-wrap justify-between gap-2 text-xs">
				<span class="text-error" data-testid="ask-soc-problem">{{ touched && problem ? problem : "" }}</span>
				<span
					:class="length > QUESTION_MAX ? 'text-error' : 'text-secondary'"
					class="tabular-nums"
					data-testid="ask-soc-count"
				>
					{{ length }} / {{ QUESTION_MAX }}
				</span>
			</div>

			<fieldset class="m-0 flex flex-col gap-2 border-0 p-0">
				<legend class="mb-2 text-sm font-medium">How urgent is it?</legend>
				<n-radio-group v-model:value="urgency" :disabled="sending" data-testid="ask-soc-urgency">
					<div class="flex flex-wrap gap-x-6 gap-y-2">
						<n-radio v-for="option of URGENCY_OPTIONS" :key="option.value" :value="option.value">
							<span class="font-medium">{{ option.label }}</span>
							<span class="text-secondary ml-1 text-xs">{{ option.description }}</span>
						</n-radio>
					</div>
				</n-radio-group>
			</fieldset>

			<fieldset v-if="entity === 'alert'" class="m-0 flex flex-col gap-2 border-0 p-0">
				<legend class="mb-2 text-sm font-medium">Where should it go?</legend>
				<n-radio-group v-model:value="target" :disabled="sending" data-testid="ask-soc-target">
					<div class="flex flex-col gap-2">
						<n-radio
							v-for="option of targets"
							:key="option.value"
							:value="option.value"
							:data-testid="`ask-soc-target-${option.value}`"
						>
							<span class="font-medium">{{ option.label }}</span>
							<span class="text-secondary ml-1 text-xs">{{ option.description }}</span>
						</n-radio>
					</div>
				</n-radio-group>
			</fieldset>

			<n-alert v-if="sendError" type="error" :bordered="false" data-testid="ask-soc-error">
				{{ sendError }}
			</n-alert>

			<div>
				<n-button
					type="primary"
					attr-type="submit"
					:loading="sending"
					:disabled="sending"
					data-testid="ask-soc-send"
				>
					<template #icon>
						<Icon name="carbon:send" />
					</template>
					Send to the SOC
				</n-button>
			</div>
		</form>

		<section class="flex flex-col gap-3" aria-labelledby="ask-soc-history">
			<div class="flex items-center justify-between gap-2">
				<h3 id="ask-soc-history" class="m-0 text-base font-semibold">Questions to the SOC</h3>
				<n-spin v-if="loading" size="small" />
			</div>

			<n-alert v-if="listError" type="warning" :bordered="false" data-testid="ask-soc-list-error">
				<div class="flex flex-wrap items-center justify-between gap-3">
					<span>{{ listError }}</span>
					<n-button size="small" secondary @click="load()">Try again</n-button>
				</div>
			</n-alert>

			<p v-else-if="!requests.length && !loading" class="text-secondary m-0 text-sm" data-testid="ask-soc-empty">
				No question asked about this {{ entity }} yet.
			</p>

			<ul v-else class="m-0 flex list-none flex-col gap-3 p-0">
				<li
					v-for="request of requests"
					:key="request.id"
					class="border-default flex flex-col gap-2 rounded-lg border px-4 py-3"
					:data-status="request.status"
					data-testid="ask-soc-request"
				>
					<div class="flex flex-wrap items-center gap-2 text-sm">
						<n-tag
							size="small"
							:bordered="false"
							:type="request.status === 'answered' ? 'success' : 'info'"
							data-testid="ask-soc-request-status"
						>
							<template #icon>
								<Icon
									:name="request.status === 'answered' ? 'carbon:checkmark-outline' : 'carbon:time'"
								/>
							</template>
							{{ STATUS_LABELS[request.status] }}
						</n-tag>
						<span class="text-secondary">Urgency: {{ URGENCY_LABELS[request.urgency] }}</span>
						<span
							v-if="filedOn(request, entity)"
							class="text-secondary"
							data-testid="ask-soc-request-filed"
						>
							· {{ filedOn(request, entity) }}
						</span>
					</div>
					<p class="text-default m-0 text-sm whitespace-pre-wrap" data-testid="ask-soc-request-question">
						<bdi>{{ request.question }}</bdi>
					</p>
					<div class="text-secondary text-xs">
						Asked by
						<bdi>{{ request.requested_by }}</bdi>
						· {{ formatDate(request.requested_at, dFormats.datetime, { tz: true }) }}
						<template v-if="request.answered_at">
							· answered {{ formatDate(request.answered_at, dFormats.datetime, { tz: true }) }}
						</template>
					</div>
				</li>
			</ul>
		</section>
	</div>
</template>

<script setup lang="ts">
import type { ApiError } from "@/types/common"
import type { SocRequest, SocRequestAlertTarget, SocRequestUrgency } from "@/types/socRequests"
import { NAlert, NButton, NInput, NRadio, NRadioGroup, NSpin, NTag, useMessage } from "naive-ui"
import { computed, onBeforeMount, ref, watch } from "vue"
import Api from "@/api"
import Icon from "@/components/common/Icon.vue"
import { useLatestRequest } from "@/composables/common/useLatestRequest"
import { useSettingsStore } from "@/stores/settings"
import { getApiErrorMessage } from "@/utils"
import { formatDate } from "@/utils/format"
import {
	filedOn,
	normalizeQuestion,
	QUESTION_MAX,
	questionLength,
	questionProblem,
	STATUS_LABELS,
	targetOptions,
	URGENCY_LABELS,
	URGENCY_OPTIONS
} from "./askSoc"

/**
 * "Ask the SOC" (#1305) on an alert or a case of the portal: the form, and the questions
 * already asked about it with whether the SOC answered. Shown only when the customer lets its
 * portal users ask (the parent checks the switch). A sent question is a comment on the target,
 * and on an alert may open a case: `asked` tells the parent to read the alert or case again.
 */

const { entity, entityId } = defineProps<{
	entity: "alert" | "case"
	entityId: number
}>()

const emit = defineEmits<{ asked: [request: SocRequest] }>()

const message = useMessage()
const dFormats = useSettingsStore().dateFormat

const question = ref("")
const urgency = ref<SocRequestUrgency>("normal")
const target = ref<SocRequestAlertTarget>("case")
const touched = ref(false)
const sending = ref(false)
const sendError = ref<string | null>(null)

const length = computed(() => questionLength(question.value))
const problem = computed(() => questionProblem(question.value))

const requests = ref<SocRequest[]>([])
const openCaseId = ref<number | null>(null)
const listError = ref<string | null>(null)
const { loading, run } = useLatestRequest()
const targets = computed(() => targetOptions(openCaseId.value))

function load() {
	listError.value = null
	return run(
		async signal => {
			const res =
				entity === "alert"
					? await Api.socRequests.listForAlert(entityId, signal)
					: await Api.socRequests.listForCase(entityId, signal)
			requests.value = res.data.requests ?? []
			openCaseId.value = res.data.open_case_id ?? null
		},
		err => {
			listError.value = getApiErrorMessage(err as ApiError) || "Could not load the questions."
		}
	)
}

async function send() {
	touched.value = true
	sendError.value = null
	if (problem.value) return

	sending.value = true
	try {
		const payload = { question: normalizeQuestion(question.value), urgency: urgency.value }
		const res =
			entity === "alert"
				? await Api.socRequests.askOnAlert(entityId, { ...payload, target: target.value })
				: await Api.socRequests.askOnCase(entityId, payload)
		message.success("Your question was sent to the SOC")
		question.value = ""
		urgency.value = "normal"
		target.value = "case"
		touched.value = false
		emit("asked", res.data.request)
		await load()
	} catch (err) {
		// Refusals are the backend's fixed texts (switched off, too soon, the daily limit).
		sendError.value = getApiErrorMessage(err as ApiError) || "Your question could not be sent. Please try again."
	} finally {
		sending.value = false
	}
}

watch(
	() => entityId,
	() => {
		load()
	}
)

onBeforeMount(() => {
	load()
})
</script>
