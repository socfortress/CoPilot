<template>
	<n-spin :show="loading" class="min-h-40">
		<div class="flex flex-col gap-6">
			<AlertReportReviewPanelReplay :report :existing-review />

			<AlertReportReviewPanelForm v-model:form="form" :report />

			<AlertReportReviewPanelIocs v-model:state="iocState" v-model:iocs="iocs" :report />

			<!-- Submit review -->
			<div class="flex items-center justify-end gap-3">
				<span v-if="submitting" class="text-secondary text-sm">Saving…</span>
				<n-button :disabled="submitting || !canSubmit" type="primary" @click="handleSubmit">
					{{ existingReview ? "Update review" : "Submit review" }}
				</n-button>
			</div>

			<!-- Inline teach-the-palace -->
			<n-collapse>
				<n-collapse-item name="teach-palace" title="Teach the palace">
					<div class="flex flex-col gap-4 p-2">
						<div class="text-secondary text-sm">
							Queue a lesson for the MemPalace. The NanoClaw drainer ingests these asynchronously.
						</div>
						<div class="grid grid-cols-1 gap-3 md:grid-cols-2">
							<div>
								<div class="mb-1 font-medium">Room</div>
								<n-select
									v-model:value="lesson.lesson_type"
									:options="lessonTypeOptions"
									placeholder="Select room"
								/>
							</div>
							<div>
								<div class="mb-1 font-medium">Durability</div>
								<div class="flex items-center gap-3">
									<n-switch v-model:value="lessonDurable" />
									<span class="text-secondary text-sm">
										{{ lessonDurable ? "Durable (persistent)" : "One-off (single session)" }}
									</span>
								</div>
							</div>
						</div>
						<div>
							<div class="mb-1 font-medium">Lesson text</div>
							<n-input
								v-model:value="lesson.lesson_text"
								type="textarea"
								placeholder="What should the palace remember?"
								:autosize="{ minRows: 3, maxRows: 10 }"
							/>
						</div>

						<!-- Similar-lesson preview -->
						<div v-if="similarLoading || similarLessons.length" class="flex flex-col gap-2">
							<div class="text-secondary text-sm">
								<span v-if="similarLoading">Searching similar lessons…</span>
								<span v-else>Similar lessons already in the palace:</span>
							</div>
							<div v-if="!similarLoading" class="flex flex-col gap-1">
								<div
									v-for="(hit, idx) of similarLessons"
									:key="hit.id ?? idx"
									class="border-color bg-secondary rounded border p-2 text-sm"
								>
									<div class="flex items-center justify-between gap-2">
										<span class="text-secondary">
											{{ hit.room || "—" }}
											<template v-if="hit.score !== null && hit.score !== undefined">
												· score {{ hit.score.toFixed(2) }}
											</template>
										</span>
									</div>
									<div>{{ hit.text || "(no text)" }}</div>
								</div>
							</div>
						</div>

						<div class="flex items-center justify-end gap-3">
							<span v-if="queuing" class="text-secondary text-sm">Queuing…</span>
							<n-button :disabled="queuing || !canQueueLesson" @click="handleQueueLesson">
								Queue lesson
							</n-button>
						</div>
					</div>
				</n-collapse-item>
			</n-collapse>
		</div>
	</n-spin>
</template>

<script setup lang="ts">
import type {
	AiAnalystIoc,
	AiAnalystReport,
	AiAnalystReview,
	Durability,
	IocVerdictCorrection,
	LessonType,
	PalaceSearchHit,
	SubmitReviewPayload
} from "@/types/aiAnalyst.d"
import { NButton, NCollapse, NCollapseItem, NInput, NSelect, NSpin, NSwitch, useMessage } from "naive-ui"
import { computed, onBeforeMount, ref, toRefs, watch } from "vue"
import Api from "@/api"
import AlertReportReviewPanelReplay from "./AlertReportReviewPanelReplay.vue"
import AlertReportReviewPanelForm, { type FormState } from "./AlertReportReviewPanelForm.vue"
import AlertReportReviewPanelIocs from "./AlertReportReviewPanelIocs.vue"
import { getApiErrorMessage } from "@/utils"
import type { ApiError } from "@/types/common"

interface IocState {
	verdict_correct: boolean
	note: string
}

const props = defineProps<{
	report: AiAnalystReport
}>()

const { report } = toRefs(props)

const message = useMessage()
const loading = ref(false)
const submitting = ref(false)
const queuing = ref(false)

const iocState = ref<Map<number, IocState>>(new Map())
const iocs = ref<AiAnalystIoc[]>([])

const existingReview = ref<AiAnalystReview | null>(null)

const form = ref<FormState>({
	overall_verdict: null,
	template_choice: null,
	rating_instructions: 3,
	rating_artifacts: 3,
	rating_severity: 3,
	missing_steps: "",
	suggested_edits: ""
})

// --- Teach the palace ---
const lessonTypeOptions: { label: string; value: LessonType }[] = [
	{ label: "Environment", value: "environment" },
	{ label: "False positives", value: "false_positives" },
	{ label: "Assets", value: "assets" },
	{ label: "Threat intel", value: "threat_intel" },
	{ label: "Alerts", value: "alerts" }
]

const lesson = ref<{ lesson_type: LessonType | null; lesson_text: string }>({
	lesson_type: null,
	lesson_text: ""
})
const lessonDurable = ref(true)
const lessonDurability = computed<Durability>(() => (lessonDurable.value ? "durable" : "one_off"))

const canQueueLesson = computed(() => !!lesson.value.lesson_type && lesson.value.lesson_text.trim().length > 0)

// Debounced similar-lesson preview — re-run when the user pauses typing OR
// changes the room. Keeps the lesson draft honest against what's already stored.
const similarLessons = ref<PalaceSearchHit[]>([])
const similarLoading = ref(false)
let similarTimer: ReturnType<typeof setTimeout> | null = null

// At least overall_verdict must be set
const canSubmit = computed(() => form.value.overall_verdict !== null)

function hydrateFromReview(r: AiAnalystReview) {
	form.value.overall_verdict = (r.overall_verdict as "up" | "down" | null) ?? null
	form.value.template_choice = (r.template_choice as "correct" | "wrong" | "partial" | null) ?? null
	form.value.rating_instructions = r.rating_instructions ?? 3
	form.value.rating_artifacts = r.rating_artifacts ?? 3
	form.value.rating_severity = r.rating_severity ?? 3
	form.value.missing_steps = r.missing_steps ?? ""
	form.value.suggested_edits = r.suggested_edits ?? ""

	const next = new Map<number, IocState>()
	for (const ir of r.ioc_reviews || []) {
		next.set(ir.ioc_id, { verdict_correct: ir.verdict_correct, note: ir.note ?? "" })
	}
	iocState.value = next
}

async function loadReview() {
	loading.value = true

	try {
		const mineRes = await Api.aiAnalyst.getMyReview(report.value.id)

		if (mineRes.data.success) {
			existingReview.value = mineRes.data.review ?? null
			if (existingReview.value) hydrateFromReview(existingReview.value)
		}
	} catch (err) {
		message.error(getApiErrorMessage(err as ApiError) || "Failed to load review data")
	} finally {
		loading.value = false
	}
}

function buildReviewPayload(): SubmitReviewPayload {
	const ioc_reviews: IocVerdictCorrection[] = []
	for (const ioc of iocs.value) {
		const st = iocState.value.get(ioc.id)
		if (!st) continue
		// Only include corrections that represent meaningful input:
		// verdict marked wrong, OR reviewer left a note.
		if (st.verdict_correct === false || st.note.trim().length > 0) {
			ioc_reviews.push({
				ioc_id: ioc.id,
				verdict_correct: st.verdict_correct,
				...(st.note.trim() ? { note: st.note.trim() } : {})
			})
		}
	}
	return {
		...(form.value.overall_verdict ? { overall_verdict: form.value.overall_verdict } : {}),
		...(form.value.template_choice ? { template_choice: form.value.template_choice } : {}),
		...(report.value.report_markdown && existingReview.value?.template_used
			? { template_used: existingReview.value.template_used }
			: {}),
		rating_instructions: form.value.rating_instructions,
		rating_artifacts: form.value.rating_artifacts,
		rating_severity: form.value.rating_severity,
		...(form.value.missing_steps.trim() ? { missing_steps: form.value.missing_steps.trim() } : {}),
		...(form.value.suggested_edits.trim() ? { suggested_edits: form.value.suggested_edits.trim() } : {}),
		ioc_reviews
	}
}

async function handleSubmit() {
	if (!canSubmit.value) return
	submitting.value = true
	try {
		const res = await Api.aiAnalyst.submitReview(report.value.id, buildReviewPayload())
		if (res.data.success) {
			existingReview.value = res.data.review
			message.success(res.data.message || "Review saved")
		} else {
			message.warning(res.data.message || "Failed to save review")
		}
	} catch (err) {
		message.error(getApiErrorMessage(err as ApiError) || "Failed to save review")
	} finally {
		submitting.value = false
	}
}

async function handleQueueLesson() {
	if (!canQueueLesson.value || !lesson.value.lesson_type) return
	queuing.value = true
	try {
		const res = await Api.aiAnalyst.queuePalaceLesson({
			customer_code: report.value.customer_code,
			lesson_type: lesson.value.lesson_type,
			lesson_text: lesson.value.lesson_text.trim(),
			durability: lessonDurability.value,
			...(existingReview.value ? { review_id: existingReview.value.id } : {})
		})
		if (res.data.success) {
			message.success(res.data.message || "Lesson queued")
			lesson.value.lesson_text = ""
			similarLessons.value = []
		} else {
			message.warning(res.data.message || "Failed to queue lesson")
		}
	} catch (err) {
		message.error(getApiErrorMessage(err as ApiError) || "Failed to queue lesson")
	} finally {
		queuing.value = false
	}
}

function scheduleSimilarSearch() {
	if (similarTimer) clearTimeout(similarTimer)
	const text = lesson.value.lesson_text.trim()
	if (text.length < 8 || !lesson.value.lesson_type) {
		similarLessons.value = []
		similarLoading.value = false
		return
	}
	similarLoading.value = true
	similarTimer = setTimeout(async () => {
		try {
			const res = await Api.aiAnalyst.searchPalaceLessons(
				report.value.customer_code,
				text,
				lesson.value.lesson_type ?? undefined,
				5
			)
			if (res.data.success) similarLessons.value = res.data.lessons || []
			else similarLessons.value = []
		} catch {
			// Non-fatal — preview is best-effort
			similarLessons.value = []
		} finally {
			similarLoading.value = false
		}
	}, 500)
}

watch(() => [lesson.value.lesson_text, lesson.value.lesson_type], scheduleSimilarSearch)

onBeforeMount(() => {
	loadReview()
})
</script>
