<template>
	<n-drawer v-model:show="show" :width="520" placement="right">
		<n-drawer-content v-if="review" closable>
			<template #header>Review for report #{{ review.report_id }}</template>
			<div class="flex flex-col gap-3">
				<div class="flex flex-wrap items-center gap-2">
					<Badge
						v-if="review.overall_verdict"
						type="splitted"
						bright
						:color="review.overall_verdict === 'up' ? 'success' : 'danger'"
					>
						<template #label>Verdict</template>
						<template #value>
							{{ review.overall_verdict === "up" ? "Up" : "Down" }}
						</template>
					</Badge>
					<Badge v-if="review.template_used" type="splitted">
						<template #label>Template</template>
						<template #value>{{ review.template_used }}</template>
					</Badge>
					<Badge v-if="review.template_choice" type="splitted" bright>
						<template #label>Template choice</template>
						<template #value>{{ review.template_choice }}</template>
					</Badge>
				</div>

				<CardKV v-if="review.missing_steps">
					<template #key>Missing steps</template>
					<template #value>{{ review.missing_steps }}</template>
				</CardKV>
				<CardKV v-if="review.suggested_edits">
					<template #key>Suggested edits</template>
					<template #value>{{ review.suggested_edits }}</template>
				</CardKV>

				<div v-if="review.ioc_reviews.length" class="flex flex-col gap-2">
					<div class="font-medium">IOC corrections</div>
					<div
						v-for="ir of review.ioc_reviews"
						:key="ir.id"
						class="border-color bg-secondary rounded border p-2 text-sm"
					>
						<div class="flex items-center gap-2">
							<Badge type="splitted" :color="ir.verdict_correct ? 'success' : 'danger'">
								<template #label>IOC {{ ir.ioc_id }}</template>
								<template #value>
									{{ ir.verdict_correct ? "Correct" : "Wrong" }}
								</template>
							</Badge>
						</div>
						<div v-if="ir.note" class="text-secondary mt-1">{{ ir.note }}</div>
					</div>
				</div>
			</div>
		</n-drawer-content>
	</n-drawer>
</template>

<script setup lang="ts">
import type { AiAnalystReview } from "@/types/aiAnalyst.d"
import { NDrawer, NDrawerContent } from "naive-ui"
import Badge from "@/components/common/Badge.vue"
import CardKV from "@/components/common/cards/CardKV.vue"

defineProps<{
	review: AiAnalystReview | null
}>()

const show = defineModel<boolean>("show")
</script>
