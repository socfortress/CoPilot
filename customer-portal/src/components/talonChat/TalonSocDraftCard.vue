<template>
	<section
		class="border-default bg-default flex flex-col gap-3 rounded-lg border px-4 py-3"
		:data-status="draft?.status ?? (loadErrorCode ? 'error' : 'loading')"
		data-testid="talon-draft-card"
	>
		<header class="flex flex-wrap items-center gap-2">
			<Icon name="carbon:chat" :size="16" class="text-secondary" />
			<h4 class="m-0 text-sm font-semibold">{{ $t("talonChat.draft.title") }}</h4>
			<span v-if="draft" class="text-secondary text-xs" data-testid="talon-draft-target">
				{{
					draft.target.kind === "alert"
						? $t("talonChat.draft.aboutAlert", { id: draft.target.id })
						: $t("talonChat.draft.aboutCase", { id: draft.target.id })
				}}
			</span>
		</header>

		<div v-if="loading && !draft" class="text-secondary flex items-center gap-2 text-xs">
			<n-spin size="small" />
			{{ $t("talonChat.draft.loading") }}
		</div>

		<n-alert v-else-if="loadErrorCode" type="warning" :bordered="false" data-testid="talon-draft-load-error">
			<div class="flex flex-wrap items-center justify-between gap-3">
				<span>{{ loadErrorCode === "draft_not_found" ? $t("talonChat.draft.unavailable") : $t("talonChat.draft.loadFailed") }}</span>
				<n-button v-if="loadErrorCode !== 'draft_not_found'" size="small" secondary @click="load()">
					{{ $t("common.actions.tryAgain") }}
				</n-button>
			</div>
		</n-alert>

		<template v-else-if="draft">
			<!-- Pending: the user edits, picks the urgency and where it goes, then sends or discards. -->
			<template v-if="draft.status === 'pending'">
				<template v-if="canDraft">
					<p class="text-secondary m-0 text-xs">{{ $t("talonChat.draft.intro") }}</p>
					<form class="flex flex-col gap-3" data-testid="talon-draft-form" @submit.prevent="submit()">
						<n-input
							v-model:value="question"
							type="textarea"
							:autosize="{ minRows: 3, maxRows: 10 }"
							:status="touched && problem ? 'error' : undefined"
							:disabled="busy"
							:input-props="{ 'aria-label': $t('talonChat.draft.questionLabel') }"
							data-testid="talon-draft-question"
							@blur="touched = true"
						/>
						<div class="-mt-2 flex flex-wrap justify-between gap-2 text-xs">
							<span class="text-error" data-testid="talon-draft-problem">{{ touched && problem ? problem : "" }}</span>
							<span :class="length > QUESTION_MAX ? 'text-error' : 'text-secondary'" class="tabular-nums" data-testid="talon-draft-count">
								{{ length }} / {{ QUESTION_MAX }}
							</span>
						</div>

						<fieldset class="m-0 flex flex-col gap-2 border-0 p-0">
							<legend class="mb-2 text-sm font-medium">{{ $t("talonChat.draft.urgencyLegend") }}</legend>
							<n-radio-group v-model:value="urgency" :disabled="busy" data-testid="talon-draft-urgency">
								<div class="flex flex-wrap gap-x-6 gap-y-2">
									<n-radio v-for="option of URGENCY_OPTIONS" :key="option.value" :value="option.value">
										<span class="font-medium">{{ option.label }}</span>
										<span class="text-secondary ml-1 text-xs">{{ option.description }}</span>
									</n-radio>
								</div>
							</n-radio-group>
							<span v-if="touched && !urgency" class="text-error text-xs" data-testid="talon-draft-urgency-problem">
								{{ $t("talonChat.draft.urgencyRequired") }}
							</span>
						</fieldset>

						<fieldset v-if="draft.target.kind === 'alert'" class="m-0 flex flex-col gap-2 border-0 p-0">
							<legend class="mb-2 text-sm font-medium">{{ $t("talonChat.draft.fileOnLegend") }}</legend>
							<n-radio-group v-model:value="fileOn" :disabled="busy" data-testid="talon-draft-file-on">
								<div class="flex flex-col gap-2">
									<n-radio v-for="option of FILE_ON" :key="option" :value="option" :data-testid="`talon-draft-file-on-${option}`">
										<span class="font-medium">{{ $t(`talonChat.draft.fileOn.${option}`) }}</span>
										<span class="text-secondary ml-1 text-xs">{{ $t(`talonChat.draft.fileOn.${option}Hint`) }}</span>
									</n-radio>
								</div>
							</n-radio-group>
						</fieldset>

						<n-alert v-if="actionErrorCode" type="error" :bordered="false" data-testid="talon-draft-error">
							{{ errorText(actionErrorCode) }}
						</n-alert>

						<div class="flex flex-wrap gap-2">
							<n-button type="primary" attr-type="submit" :loading="submitting" :disabled="busy" data-testid="talon-draft-submit">
								<template #icon><Icon name="carbon:send" /></template>
								{{ $t("talonChat.draft.submit") }}
							</n-button>
							<n-button secondary :loading="discarding" :disabled="busy" data-testid="talon-draft-discard" @click="discard()">
								{{ $t("talonChat.draft.discard") }}
							</n-button>
						</div>
					</form>
				</template>
				<template v-else>
					<p class="m-0 text-sm break-words whitespace-pre-wrap" data-testid="talon-draft-question-text">
						<span>{{ draft.question }}</span>
					</p>
					<p class="text-secondary m-0 text-xs" data-testid="talon-draft-off">{{ $t("talonChat.draft.socRequestsOff") }}</p>
				</template>
			</template>

			<template v-else>
				<p class="m-0 text-sm break-words whitespace-pre-wrap" data-testid="talon-draft-question-text">
					<span>{{ draft.question }}</span>
				</p>
				<div class="flex flex-wrap items-center gap-2">
					<n-tag size="small" :bordered="false" :type="STATUS_TAG[draft.status]" data-testid="talon-draft-status">
						{{ $t(`talonChat.draft.status.${draft.status}`) }}
					</n-tag>
					<n-button v-if="draft.status === 'submitting'" size="tiny" secondary :loading data-testid="talon-draft-refresh" @click="load()">
						{{ $t("talonChat.draft.refresh") }}
					</n-button>
				</div>
				<p v-if="draft.status === 'submitted'" class="text-secondary m-0 text-xs" data-testid="talon-draft-submitted">
					{{
						draft.copilot_ref
							? $t("talonChat.draft.submittedText", { id: draft.copilot_ref })
							: $t("talonChat.draft.submittedNoId")
					}}
				</p>
			</template>
		</template>
	</section>
</template>

<script setup lang="ts">
import type { TagProps } from "naive-ui"
import type { TalonDraftFileOn, TalonDraftStatus, TalonDraftUrgency, TalonSocDraft } from "@/types/talonChat"
import { NAlert, NButton, NInput, NRadio, NRadioGroup, NSpin, NTag } from "naive-ui"
import { computed, ref, watch } from "vue"
import Api from "@/api"
import Icon from "@/components/common/Icon.vue"
import { normalizeQuestion, QUESTION_MAX, questionLength, questionProblem, URGENCY_OPTIONS } from "@/components/socRequests/askSoc"
import { useLatestRequest } from "@/composables/common/useLatestRequest"
import { errorCodeOf, errorText } from "./talonChat"

/**
 * A question Talon drafted for the SOC (`ask_the_soc`, talon-analyst D97 Q4). Read back by its id
 * from CoPilot, never from the stream's text. The user may edit the question (the Ask the SOC
 * form's own `clean_question` limits), must pick the urgency (Talon never sets it) and, for an
 * alert, where it is filed (the alert's case by default), then sends or discards it. CoPilot
 * claims, files as the user and records the outcome; the card shows what came of it.
 *
 * The parent shows this card only to a user who may change the customer's data; `canDraft` is
 * the availability's word on whether the customer takes questions to the SOC at all.
 */
const { draftId, canDraft = false } = defineProps<{
	draftId: string
	canDraft?: boolean
}>()

const FILE_ON: TalonDraftFileOn[] = ["case", "alert"]
const STATUS_TAG: Record<TalonDraftStatus, NonNullable<TagProps["type"]>> = {
	pending: "default",
	submitting: "info",
	submitted: "success",
	discarded: "default",
	expired: "warning"
}

const draft = ref<TalonSocDraft | null>(null)
const loadErrorCode = ref<string | null>(null)
const { loading, run } = useLatestRequest()

const question = ref("")
// The customer picks the urgency: nothing is chosen for them.
const urgency = ref<TalonDraftUrgency | null>(null)
// CoPilot's form default for a question on an alert: its case.
const fileOn = ref<TalonDraftFileOn>("case")
const touched = ref(false)
const submitting = ref(false)
const discarding = ref(false)
const actionErrorCode = ref<string | null>(null)

const busy = computed(() => submitting.value || discarding.value)
const length = computed(() => questionLength(question.value))
const problem = computed(() => questionProblem(question.value))

function show(next: TalonSocDraft) {
	const first = !draft.value || draft.value.id !== next.id
	draft.value = next
	if (first) question.value = next.question ?? ""
}

function load() {
	loadErrorCode.value = null
	return run(
		async signal => {
			const res = await Api.talonChat.getDraft(draftId, signal)
			show(res.data)
		},
		err => {
			loadErrorCode.value = errorCodeOf(err) ?? "unknown"
		}
	)
}

async function submit() {
	touched.value = true
	actionErrorCode.value = null
	if (!draft.value || problem.value || !urgency.value) return

	submitting.value = true
	try {
		const payload = {
			question: normalizeQuestion(question.value),
			urgency: urgency.value,
			...(draft.value.target.kind === "alert" ? { file_on: fileOn.value } : {})
		}
		const res = await Api.talonChat.submitDraft(draftId, payload)
		const requestId = res.data?.request_id
		draft.value = {
			...draft.value,
			status: "submitted",
			question: payload.question,
			urgency: payload.urgency,
			copilot_ref: requestId === undefined || requestId === null ? null : String(requestId)
		}
	} catch (err) {
		const code = errorCodeOf(err)
		if (code === "draft_expired" && draft.value) {
			draft.value = { ...draft.value, status: "expired" }
		} else if (code === "draft_conflict") {
			// Sent or discarded elsewhere (another tab): show what it is now.
			await load()
		} else {
			actionErrorCode.value = code ?? "unknown"
		}
	} finally {
		submitting.value = false
	}
}

async function discard() {
	actionErrorCode.value = null
	discarding.value = true
	try {
		const res = await Api.talonChat.discardDraft(draftId)
		if (res.data?.id) show(res.data)
		else if (draft.value) draft.value = { ...draft.value, status: "discarded" }
	} catch (err) {
		const code = errorCodeOf(err)
		if (code === "draft_conflict" || code === "draft_expired") await load()
		else actionErrorCode.value = code ?? "unknown"
	} finally {
		discarding.value = false
	}
}

watch(
	() => draftId,
	() => {
		draft.value = null
		urgency.value = null
		fileOn.value = "case"
		touched.value = false
		actionErrorCode.value = null
		load()
	},
	{ immediate: true }
)
</script>
