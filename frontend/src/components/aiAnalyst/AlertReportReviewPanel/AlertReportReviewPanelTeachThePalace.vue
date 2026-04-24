<template>
	<n-card size="small" title="Teach the palace" segmented>
		<div class="flex flex-col gap-6">
			<p class="text-sm">Queue a lesson for the MemPalace. The NanoClaw drainer ingests these asynchronously.</p>

			<div class="grid grid-cols-1 gap-6 md:grid-cols-2">
				<n-form-item label="Room" :show-feedback="false">
					<n-select
						v-model:value="lesson.lesson_type"
						:options="lessonTypeOptions"
						placeholder="Select room"
					/>
				</n-form-item>

				<n-form-item label="Durability" :show-feedback="false">
					<div class="flex items-center gap-3">
						<n-switch v-model:value="lesson.durable" />
						<span class="text-secondary text-sm">
							{{ lesson.durable ? "Durable (persistent)" : "One-off (single session)" }}
						</span>
					</div>
				</n-form-item>
			</div>

			<n-form-item label="Lesson text" :show-feedback="false">
				<n-input
					v-model:value="lesson.lesson_text"
					type="textarea"
					placeholder="What should the palace remember?"
					:autosize="{ minRows: 3, maxRows: 10 }"
				/>
			</n-form-item>

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
				<n-button
					:disabled="!canQueueLesson"
					:loading="queuing"
					type="primary"
					secondary
					@click="handleQueueLesson"
				>
					{{ queuing ? "Queueing..." : "Queue lesson" }}
				</n-button>
			</div>
		</div>
	</n-card>
</template>

<script setup lang="ts">
import type { AiAnalystReport, AiAnalystReview, Durability, LessonType, PalaceSearchHit } from "@/types/aiAnalyst.d"
import type { ApiError } from "@/types/common"
import { NButton, NCard, NFormItem, NInput, NSelect, NSwitch, useMessage } from "naive-ui"
import { computed, ref, toRefs, watch } from "vue"
import Api from "@/api"
import { getApiErrorMessage } from "@/utils"

const props = defineProps<{
	report: AiAnalystReport
	existingReview: AiAnalystReview | null
}>()

const { report, existingReview } = toRefs(props)

const message = useMessage()
const queuing = ref(false)

const lessonTypeOptions: { label: string; value: LessonType }[] = [
	{ label: "Environment", value: "environment" },
	{ label: "False positives", value: "false_positives" },
	{ label: "Assets", value: "assets" },
	{ label: "Threat intel", value: "threat_intel" },
	{ label: "Alerts", value: "alerts" }
]

const lesson = ref<{ lesson_type: LessonType | null; lesson_text: string; durable: boolean }>({
	lesson_type: null,
	lesson_text: "",
	durable: true
})
const lessonDurability = computed<Durability>(() => (lesson.value.durable ? "durable" : "one_off"))

const canQueueLesson = computed(() => !!lesson.value.lesson_type && lesson.value.lesson_text.trim().length > 0)

// Debounced similar-lesson preview — re-run when the user pauses typing OR
// changes the room. Keeps the lesson draft honest against what's already stored.
const similarLessons = ref<PalaceSearchHit[]>([])
const similarLoading = ref(false)
let similarTimer: ReturnType<typeof setTimeout> | null = null

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
</script>
