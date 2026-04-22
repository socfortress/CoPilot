<template>
	<n-spin :show="loading" class="min-h-40">
		<div class="flex flex-col gap-6">
			<!-- Toolbar: mode banner + replay trigger -->
			<div class="flex flex-wrap items-center justify-between gap-3">
				<div v-if="existingReview" class="flex items-center gap-2">
					<Badge type="splitted" bright color="success">
						<template #label>Already reviewed</template>
						<template #value>Editing your previous submission</template>
					</Badge>
					<span v-if="existingReview.updated_at" class="text-secondary text-sm">
						Last edited {{ formatTs(existingReview.updated_at) }}
					</span>
					<span v-else class="text-secondary text-sm">
						Submitted {{ formatTs(existingReview.created_at) }}
					</span>
				</div>
				<div v-else />
				<n-button size="small" @click="showReplayModal = true">
					<template #icon>
						<Icon :name="ReplayIcon" :size="14" />
					</template>
					Replay with different template
				</n-button>
			</div>

			<ReplayModal v-model:show="showReplayModal" :report="report" @replayed="onReplayed" />

			<!-- Rubric -->
			<CardEntity size="small" embedded>
				<template #default>
					<div class="flex flex-col gap-4">
						<!-- Overall verdict -->
						<div>
							<div class="mb-1 font-medium">Overall verdict</div>
							<n-radio-group v-model:value="form.overall_verdict">
								<n-radio-button value="up">
									<Icon :name="ThumbUpIcon" :size="14" class="mr-1" />
									Good
								</n-radio-button>
								<n-radio-button value="down">
									<Icon :name="ThumbDownIcon" :size="14" class="mr-1" />
									Bad
								</n-radio-button>
							</n-radio-group>
						</div>

						<!-- Template choice -->
						<div>
							<div class="mb-1 font-medium">Template used</div>
							<div v-if="report.report_markdown === null" class="text-secondary text-sm">
								No template recorded on this report.
							</div>
							<n-radio-group v-model:value="form.template_choice">
								<n-radio value="correct">Correct template</n-radio>
								<n-radio value="partial">Partially correct</n-radio>
								<n-radio value="wrong">Wrong template</n-radio>
							</n-radio-group>
						</div>

						<!-- Ratings -->
						<div class="grid grid-cols-1 gap-4 md:grid-cols-3">
							<div>
								<div class="mb-1 font-medium">Instructions quality</div>
								<n-slider
									v-model:value="form.rating_instructions"
									:min="1"
									:max="5"
									:step="1"
									:marks="rateMarks"
								/>
							</div>
							<div>
								<div class="mb-1 font-medium">Artifact collection</div>
								<n-slider
									v-model:value="form.rating_artifacts"
									:min="1"
									:max="5"
									:step="1"
									:marks="rateMarks"
								/>
							</div>
							<div>
								<div class="mb-1 font-medium">Severity assessment</div>
								<n-slider
									v-model:value="form.rating_severity"
									:min="1"
									:max="5"
									:step="1"
									:marks="rateMarks"
								/>
							</div>
						</div>

						<!-- Missing steps -->
						<div>
							<div class="mb-1 font-medium">Missing steps</div>
							<n-input
								v-model:value="form.missing_steps"
								type="textarea"
								placeholder="What investigation steps were missed?"
								:autosize="{ minRows: 2, maxRows: 6 }"
							/>
						</div>

						<!-- Suggested edits -->
						<div>
							<div class="mb-1 font-medium">Suggested prompt / template edits</div>
							<n-input
								v-model:value="form.suggested_edits"
								type="textarea"
								placeholder="How should the template or prompt be improved?"
								:autosize="{ minRows: 2, maxRows: 6 }"
							/>
						</div>
					</div>
				</template>
			</CardEntity>

			<!-- Per-IOC verdict corrections -->
			<div>
				<div class="mb-2 font-medium">IOC verdict corrections</div>
				<div class="text-secondary mb-3 text-sm">
					Toggle off any IOC where the VirusTotal verdict above was wrong. Optionally note why.
				</div>
				<div v-if="iocs.length" class="flex flex-col gap-2">
					<CardEntity v-for="ioc of iocs" :key="ioc.id" size="small" embedded>
						<template #default>
							<div class="flex flex-col gap-2">
								<div class="flex flex-wrap items-center justify-between gap-3">
									<CodeSource :code="ioc.ioc_value" />
									<div class="flex items-center gap-3">
										<Badge type="splitted" bright>
											<template #label>Type</template>
											<template #value>{{ ioc.ioc_type }}</template>
										</Badge>
										<Badge type="splitted" bright :color="verdictColor(ioc.vt_verdict)">
											<template #label>VT</template>
											<template #value>{{ ioc.vt_verdict }}</template>
										</Badge>
										<n-tooltip placement="top">
											<template #trigger>
												<n-switch
													:value="iocCorrect(ioc.id)"
													@update:value="setIocCorrect(ioc.id, $event)"
												/>
											</template>
											{{ iocCorrect(ioc.id) ? "Verdict correct" : "Verdict wrong" }}
										</n-tooltip>
									</div>
								</div>
								<n-input
									:value="iocNote(ioc.id)"
									type="textarea"
									placeholder="Optional reviewer note"
									:autosize="{ minRows: 1, maxRows: 4 }"
									@update:value="setIocNote(ioc.id, $event)"
								/>
							</div>
						</template>
					</CardEntity>
				</div>
				<n-empty v-else description="No IOCs recorded for this report" class="min-h-24 justify-center" />
			</div>

			<!-- Submit review -->
			<div class="flex items-center justify-end gap-3">
				<span v-if="submitting" class="text-secondary text-sm">Saving…</span>
				<n-button :disabled="submitting || !canSubmit" type="primary" @click="handleSubmit">
					{{ existingReview ? "Update review" : "Submit review" }}
				</n-button>
			</div>

			<!-- Inline teach-the-palace -->
			<n-collapse>
				<n-collapse-item name="teach-palace">
					<template #header>
						<div class="flex items-center gap-2 font-medium">
							<Icon :name="BrainIcon" :size="16" />
							Teach the palace
						</div>
					</template>
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
import {
	NButton,
	NCollapse,
	NCollapseItem,
	NEmpty,
	NInput,
	NRadio,
	NRadioButton,
	NRadioGroup,
	NSelect,
	NSlider,
	NSpin,
	NSwitch,
	NTooltip,
	useMessage
} from "naive-ui"
import { computed, onBeforeMount, ref, toRefs, watch } from "vue"
import Api from "@/api"
import Badge from "@/components/common/Badge.vue"
import CardEntity from "@/components/common/cards/CardEntity.vue"
import CodeSource from "@/components/common/CodeSource.vue"
import Icon from "@/components/common/Icon.vue"
import { formatDate } from "@/utils/format"
import ReplayModal from "./ReplayModal.vue"

const props = defineProps<{
	report: AiAnalystReport
}>()

const { report } = toRefs(props)

const ThumbUpIcon = "mdi:thumb-up-outline"
const ThumbDownIcon = "mdi:thumb-down-outline"
const BrainIcon = "mdi:brain"
const ReplayIcon = "carbon:restart"

const showReplayModal = ref(false)

function onReplayed(_data: Record<string, unknown> | undefined) {
	// The new report is created asynchronously by Talon's callbacks. Surface a
	// pointer so the reviewer knows where to watch — they can switch to the
	// Jobs tab or come back after the run completes.
	message.success("Replay queued — check the Jobs tab for the new run", { duration: 6000 })
}

const message = useMessage()
const loading = ref(false)
const submitting = ref(false)
const queuing = ref(false)

const existingReview = ref<AiAnalystReview | null>(null)
const iocs = ref<AiAnalystIoc[]>([])

type FormState = {
	overall_verdict: "up" | "down" | null
	template_choice: "correct" | "wrong" | "partial" | null
	rating_instructions: number
	rating_artifacts: number
	rating_severity: number
	missing_steps: string
	suggested_edits: string
}

const form = ref<FormState>({
	overall_verdict: null,
	template_choice: null,
	rating_instructions: 3,
	rating_artifacts: 3,
	rating_severity: 3,
	missing_steps: "",
	suggested_edits: ""
})

// Per-IOC review state — keyed by ioc.id so order stays stable with the list
type IocState = { verdict_correct: boolean; note: string }
const iocState = ref<Map<number, IocState>>(new Map())

function iocCorrect(iocId: number): boolean {
	return iocState.value.get(iocId)?.verdict_correct ?? true
}
function iocNote(iocId: number): string {
	return iocState.value.get(iocId)?.note ?? ""
}
function setIocCorrect(iocId: number, val: boolean) {
	const cur = iocState.value.get(iocId) ?? { verdict_correct: true, note: "" }
	iocState.value.set(iocId, { ...cur, verdict_correct: val })
}
function setIocNote(iocId: number, val: string) {
	const cur = iocState.value.get(iocId) ?? { verdict_correct: true, note: "" }
	iocState.value.set(iocId, { ...cur, note: val })
}

function verdictColor(verdict: string) {
	if (verdict === "malicious") return "danger"
	if (verdict === "suspicious") return "warning"
	if (verdict === "clean") return "success"
	return undefined
}

const rateMarks = { 1: "1", 2: "2", 3: "3", 4: "4", 5: "5" }

// At least overall_verdict must be set
const canSubmit = computed(() => form.value.overall_verdict !== null)

function formatTs(iso: string): string {
	return String(formatDate(iso, "MMM D, YYYY HH:mm"))
}

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

function seedIocDefaults() {
	// Any IOC not yet in state defaults to "verdict correct". Preserves
	// per-IOC state hydrated from an existing review.
	for (const ioc of iocs.value) {
		if (!iocState.value.has(ioc.id)) {
			iocState.value.set(ioc.id, { verdict_correct: true, note: "" })
		}
	}
}

async function loadAll() {
	loading.value = true
	try {
		const [mineRes, iocsRes] = await Promise.all([
			Api.aiAnalyst.getMyReview(report.value.id),
			Api.aiAnalyst.getIocsByReport(report.value.id)
		])
		if (iocsRes.data.success) iocs.value = iocsRes.data.iocs || []
		if (mineRes.data.success) {
			existingReview.value = mineRes.data.review ?? null
			if (existingReview.value) hydrateFromReview(existingReview.value)
		}
		seedIocDefaults()
	} catch (err: unknown) {
		const e = err as { response?: { data?: { message?: string } }; message?: string }
		message.error(e.response?.data?.message || e.message || "Failed to load review data")
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
	} catch (err: unknown) {
		const e = err as { response?: { data?: { message?: string } }; message?: string }
		message.error(e.response?.data?.message || e.message || "Failed to save review")
	} finally {
		submitting.value = false
	}
}

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

const canQueueLesson = computed(
	() => !!lesson.value.lesson_type && lesson.value.lesson_text.trim().length > 0
)

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
	} catch (err: unknown) {
		const e = err as { response?: { data?: { message?: string } }; message?: string }
		message.error(e.response?.data?.message || e.message || "Failed to queue lesson")
	} finally {
		queuing.value = false
	}
}

// Debounced similar-lesson preview — re-run when the user pauses typing OR
// changes the room. Keeps the lesson draft honest against what's already stored.
const similarLessons = ref<PalaceSearchHit[]>([])
const similarLoading = ref(false)
let similarTimer: ReturnType<typeof setTimeout> | null = null

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
	loadAll()
})
</script>
