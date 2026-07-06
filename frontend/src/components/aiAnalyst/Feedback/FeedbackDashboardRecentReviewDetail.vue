<template>
	<n-spin :show="loading">
		<div v-if="resolvedReview" class="flex flex-col gap-3">
			<div class="flex flex-wrap items-center gap-2">
				<Badge
					v-if="resolvedReview.overall_verdict"
					type="splitted"
					bright
					:color="resolvedReview.overall_verdict === 'up' ? 'success' : 'danger'"
				>
					<template #label>Verdict</template>
					<template #value>
						{{ resolvedReview.overall_verdict === "up" ? "Up" : "Down" }}
					</template>
				</Badge>
				<Badge v-if="resolvedReview.template_used" type="splitted">
					<template #label>Template</template>
					<template #value>{{ resolvedReview.template_used }}</template>
				</Badge>
				<Badge v-if="resolvedReview.template_choice" type="splitted" bright>
					<template #label>Template choice</template>
					<template #value>{{ resolvedReview.template_choice }}</template>
				</Badge>
			</div>

			<CardKV v-if="resolvedReview.missing_steps">
				<template #key>Missing steps</template>
				<template #value>{{ resolvedReview.missing_steps }}</template>
			</CardKV>
			<CardKV v-if="resolvedReview.suggested_edits">
				<template #key>Suggested edits</template>
				<template #value>{{ resolvedReview.suggested_edits }}</template>
			</CardKV>

			<n-card v-if="resolvedReview.ioc_reviews.length" size="small" title="IOC corrections" embedded>
				<div class="flex flex-col gap-2">
					<CardEntity v-for="ir of resolvedReview.ioc_reviews" :key="ir.id" embedded size="small">
						<template #default>
							<div class="flex items-center gap-2">
								<Badge type="splitted" :color="ir.verdict_correct ? 'success' : 'danger'">
									<template #label>IOC {{ ir.ioc_id }}</template>
									<template #value>
										{{ ir.verdict_correct ? "Correct" : "Wrong" }}
									</template>
								</Badge>
							</div>
						</template>
						<template v-if="ir.note" #mainExtra>
							{{ ir.note }}
						</template>
					</CardEntity>
				</div>
			</n-card>
		</div>
	</n-spin>
</template>

<script setup lang="ts">
import type { AiAnalystReview } from "@/types/ai-analyst"
import type { ApiError } from "@/types/common"
import axios from "axios"
import { NCard, NSpin, useMessage } from "naive-ui"
import { computed, ref, watch } from "vue"
import Api from "@/api"
import Badge from "@/components/common/Badge.vue"
import CardEntity from "@/components/common/cards/CardEntity.vue"
import CardKV from "@/components/common/cards/CardKV.vue"
import { getApiErrorMessage } from "@/utils"

const props = defineProps<{
	review?: AiAnalystReview | null
	reviewId?: number | null
}>()

const emit = defineEmits<{
	(e: "loaded", value: AiAnalystReview): void
}>()

const message = useMessage()
const loading = ref(false)
const fetchedReview = ref<AiAnalystReview | null>(null)

let abortController: AbortController | null = null

const resolvedReview = computed(() => props.review ?? fetchedReview.value)

function loadReview(reviewId: number) {
	abortController?.abort()
	abortController = new AbortController()
	loading.value = true

	Api.aiAnalyst
		.getReview(reviewId, abortController.signal)
		.then(res => {
			loading.value = false

			if (res.data.success && res.data.review) {
				fetchedReview.value = res.data.review
				emit("loaded", res.data.review)
			} else {
				message.warning(res.data?.message || "Review not found.")
			}
		})
		.catch(err => {
			if (!axios.isCancel(err)) {
				message.error(getApiErrorMessage(err as ApiError) || "Failed to load review.")
				loading.value = false
			}
		})
}

watch(
	() => [props.review, props.reviewId] as const,
	([review, reviewId]) => {
		if (review) {
			abortController?.abort()
			fetchedReview.value = null
			loading.value = false
			return
		}

		if (reviewId != null) {
			loadReview(reviewId)
			return
		}

		abortController?.abort()
		fetchedReview.value = null
		loading.value = false
	},
	{ immediate: true }
)

defineExpose({ loading, resolvedReview })
</script>
