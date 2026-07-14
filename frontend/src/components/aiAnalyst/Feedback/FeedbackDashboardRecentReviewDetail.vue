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
import { NCard, NSpin } from "naive-ui"
import Api from "@/api"
import Badge from "@/components/common/Badge.vue"
import CardEntity from "@/components/common/cards/CardEntity.vue"
import CardKV from "@/components/common/cards/CardKV.vue"
import { useEntityDetails } from "@/composables/useEntityDetails"

const props = defineProps<{
	review?: AiAnalystReview | null
	reviewId?: number | null
}>()

const emit = defineEmits<{
	(e: "loaded", value: AiAnalystReview): void
}>()

const { loading, entity: resolvedReview } = useEntityDetails<AiAnalystReview, number>({
	entity: () => props.review,
	id: () => props.reviewId,
	fetch: (id, signal) =>
		Api.aiAnalyst.getReview(id, signal).then(res => ({
			entity: res.data.success ? (res.data.review ?? null) : null,
			message: res.data.message
		})),
	notFoundMessage: "Review not found.",
	errorMessage: "Failed to load review.",
	onLoaded: value => emit("loaded", value)
})

defineExpose({ loading, resolvedReview })
</script>
