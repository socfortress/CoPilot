<template>
	<n-card size="small" title="Recent reviews" embedded>
		<p v-if="!stats.recent_reviews.length" class="text-sm">No reviews yet.</p>
		<div v-else class="flex flex-col gap-2">
			<CardEntity
				v-for="r of stats.recent_reviews"
				:key="r.id"
				size="small"
				hoverable
				clickable
				@click="openDrawer(r)"
			>
				<template #headerMain>
					Report #{{ r.report_id }}
					<span v-if="r.template_used" class="text-secondary ml-2 text-sm">· {{ r.template_used }}</span>
				</template>
				<template #headerExtra>
					<span class="text-secondary text-sm">
						{{ formatDate(r.updated_at ?? r.created_at, "MMM D, YYYY HH:mm") }}
					</span>
				</template>
				<template #default>
					<div class="flex flex-wrap items-center gap-3">
						<Badge
							v-if="r.overall_verdict"
							type="splitted"
							bright
							:color="r.overall_verdict === 'up' ? 'success' : 'danger'"
						>
							<template #label>Verdict</template>
							<template #value>
								{{ r.overall_verdict === "up" ? "Up" : "Down" }}
							</template>
						</Badge>
						<Badge
							v-if="r.template_choice"
							type="splitted"
							bright
							:color="tplChoiceColor(r.template_choice)"
						>
							<template #label>Template</template>
							<template #value>{{ r.template_choice }}</template>
						</Badge>
						<Badge v-if="r.rating_instructions" type="splitted">
							<template #label>Instr</template>
							<template #value>{{ r.rating_instructions }}/5</template>
						</Badge>
						<Badge v-if="r.rating_artifacts" type="splitted">
							<template #label>Artifacts</template>
							<template #value>{{ r.rating_artifacts }}/5</template>
						</Badge>
						<Badge v-if="r.rating_severity" type="splitted">
							<template #label>Severity</template>
							<template #value>{{ r.rating_severity }}/5</template>
						</Badge>
						<Badge v-if="r.ioc_reviews.length" type="splitted">
							<template #label>IOC corrections</template>
							<template #value>{{ r.ioc_reviews.length }}</template>
						</Badge>
					</div>
				</template>
			</CardEntity>
		</div>

		<!-- Drawer: full review detail -->
		<n-drawer v-model:show="showDrawer" :width="520" placement="right">
			<n-drawer-content v-if="drawerReview" closable>
				<template #header>Review for report #{{ drawerReview.report_id }}</template>
				<div class="flex flex-col gap-3">
					<div class="flex flex-wrap items-center gap-2">
						<Badge
							v-if="drawerReview.overall_verdict"
							type="splitted"
							bright
							:color="drawerReview.overall_verdict === 'up' ? 'success' : 'danger'"
						>
							<template #label>Verdict</template>
							<template #value>
								{{ drawerReview.overall_verdict === "up" ? "Up" : "Down" }}
							</template>
						</Badge>
						<Badge v-if="drawerReview.template_used" type="splitted">
							<template #label>Template</template>
							<template #value>{{ drawerReview.template_used }}</template>
						</Badge>
						<Badge v-if="drawerReview.template_choice" type="splitted" bright>
							<template #label>Template choice</template>
							<template #value>{{ drawerReview.template_choice }}</template>
						</Badge>
					</div>

					<CardKV v-if="drawerReview.missing_steps">
						<template #key>Missing steps</template>
						<template #value>{{ drawerReview.missing_steps }}</template>
					</CardKV>
					<CardKV v-if="drawerReview.suggested_edits">
						<template #key>Suggested edits</template>
						<template #value>{{ drawerReview.suggested_edits }}</template>
					</CardKV>

					<div v-if="drawerReview.ioc_reviews.length" class="flex flex-col gap-2">
						<div class="font-medium">IOC corrections</div>
						<div
							v-for="ir of drawerReview.ioc_reviews"
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
	</n-card>
</template>

<script setup lang="ts">
import type { AiAnalystReview, AiAnalystReviewStats } from "@/types/aiAnalyst.d"
import { NCard, NDrawer, NDrawerContent } from "naive-ui"
import { ref, toRefs } from "vue"
import Badge from "@/components/common/Badge.vue"
import CardEntity from "@/components/common/cards/CardEntity.vue"
import CardKV from "@/components/common/cards/CardKV.vue"
import { formatDate } from "@/utils/format"

const props = defineProps<{
	stats: AiAnalystReviewStats
}>()

const { stats } = toRefs(props)

const showDrawer = ref(false)
const drawerReview = ref<AiAnalystReview | null>(null)

function tplChoiceColor(choice: string): "success" | "warning" | "danger" | undefined {
	if (choice === "correct") return "success"
	if (choice === "partial") return "warning"
	if (choice === "wrong") return "danger"
	return undefined
}

function openDrawer(r: AiAnalystReview) {
	drawerReview.value = r
	showDrawer.value = true
}
</script>
