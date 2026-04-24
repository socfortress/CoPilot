<template>
	<n-spin :show="loading" class="min-h-40">
		<div class="flex flex-col gap-6">
			<AlertReportReviewPanelReplay :report :existing-review />

			<AlertReportReviewPanelForm v-model:form="form" :report />

			<AlertReportReviewPanelIocs v-model:state="iocState" v-model:iocs="iocs" :report />

			<!-- Submit review -->
			<div class="flex flex-col gap-0">
				<div class="flex items-center justify-between gap-3">
					<n-button text size="large" @click="showTeachPalace = !showTeachPalace">
						<template #icon>
							<Icon
								name="carbon:chevron-right"
								class="transition-transform duration-300"
								:class="{ 'rotate-90': showTeachPalace }"
							/>
						</template>
						Teach the palace
					</n-button>
					<n-button :disabled="!canSubmit" :loading="submitting" type="primary" @click="handleSubmit">
						{{ submitting ? "Saving..." : existingReview ? "Update review" : "Submit review" }}
					</n-button>
				</div>

				<!-- Inline teach-the-palace -->
				<n-collapse-transition :show="showTeachPalace">
					<div class="pt-6">
						<AlertReportReviewPanelTeachThePalace :report :existing-review />
					</div>
				</n-collapse-transition>
			</div>
		</div>
	</n-spin>
</template>

<script setup lang="ts">
import type { FormState } from "./AlertReportReviewPanelForm.vue"
import type { IocState } from "./AlertReportReviewPanelIocs.vue"
import type {
	AiAnalystIoc,
	AiAnalystReport,
	AiAnalystReview,
	IocVerdictCorrection,
	SubmitReviewPayload
} from "@/types/aiAnalyst.d"
import type { ApiError } from "@/types/common"
import { NButton, NCollapseTransition, NSpin, useMessage } from "naive-ui"
import { computed, onBeforeMount, ref, toRefs } from "vue"
import Api from "@/api"
import Icon from "@/components/common/Icon.vue"
import { getApiErrorMessage } from "@/utils"
import AlertReportReviewPanelForm from "./AlertReportReviewPanelForm.vue"
import AlertReportReviewPanelIocs from "./AlertReportReviewPanelIocs.vue"
import AlertReportReviewPanelReplay from "./AlertReportReviewPanelReplay.vue"
import AlertReportReviewPanelTeachThePalace from "./AlertReportReviewPanelTeachThePalace.vue"

const props = defineProps<{
	report: AiAnalystReport
}>()

const { report } = toRefs(props)

const message = useMessage()
const loading = ref(false)
const submitting = ref(false)

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
const showTeachPalace = ref(false)

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
		const res = await Api.aiAnalyst.getMyReview(report.value.id)

		if (res.data.success) {
			existingReview.value = res.data.review ?? null
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

onBeforeMount(() => {
	loadReview()
})
</script>
