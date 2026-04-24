<template>
	<div class="feedback-dashboard @container flex flex-col gap-5">
		<FeedbackDashboardToolbar v-model:customer="customer" v-model:loading="loading" @refresh="loadStats()" />

		<n-spin :show="loading" class="min-h-40">
			<div v-if="!customer" class="pt-6 text-center">
				<n-empty description="Pick a customer to see their review feedback" />
			</div>

			<div v-else-if="stats" class="flex flex-col gap-5">
				<FeedbackDashboardMetricTiles :stats />

				<FeedbackDashboardTemplateChoiceDistribution :stats />

				<FeedbackDashboardTemplateTable :stats />

				<!-- Recent reviews -->
				<CardEntity size="small" embedded>
					<template #headerMain>Recent reviews</template>
					<template #default>
						<div v-if="!stats.recent_reviews.length" class="text-secondary text-sm">No reviews yet.</div>
						<div v-else class="flex flex-col gap-2">
							<CardEntity
								v-for="r of stats.recent_reviews"
								:key="r.id"
								size="small"
								embedded
								hoverable
								clickable
								@click="openDrawer(r)"
							>
								<template #headerMain>
									Report #{{ r.report_id }}
									<span v-if="r.template_used" class="text-secondary ml-2 text-sm">
										· {{ r.template_used }}
									</span>
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
					</template>
				</CardEntity>
			</div>
		</n-spin>

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
	</div>
</template>

<script setup lang="ts">
import type { AiAnalystReview, AiAnalystReviewStats } from "@/types/aiAnalyst.d"
import { NDrawer, NDrawerContent, NEmpty, NSpin, useMessage } from "naive-ui"
import { ref, watch } from "vue"
import Api from "@/api"
import Badge from "@/components/common/Badge.vue"
import CardEntity from "@/components/common/cards/CardEntity.vue"
import CardKV from "@/components/common/cards/CardKV.vue"
import { getApiErrorMessage } from "@/utils"
import { formatDate } from "@/utils/format"
import FeedbackDashboardMetricTiles from "./FeedbackDashboardMetricTiles.vue"
import FeedbackDashboardTemplateChoiceDistribution from "./FeedbackDashboardTemplateChoiceDistribution.vue"
import FeedbackDashboardTemplateTable from "./FeedbackDashboardTemplateTable.vue"
import FeedbackDashboardToolbar from "./FeedbackDashboardToolbar.vue"

const message = useMessage()

const customer = ref<string | null>(null)

const loading = ref(false)
const stats = ref<AiAnalystReviewStats | null>(null)

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

async function loadStats() {
	if (!customer.value) {
		stats.value = null
		return
	}
	loading.value = true
	try {
		const res = await Api.aiAnalyst.getReviewStats(customer.value, 10)
		if (res.data.success) {
			stats.value = res.data
		} else {
			message.warning(res.data.message || "Failed to load stats")
			stats.value = null
		}
	} catch (err: unknown) {
		message.error(getApiErrorMessage(err as never) || "Failed to load stats")
		stats.value = null
	} finally {
		loading.value = false
	}
}

// Refetch stats on actual customer changes only. Wiring via @update:value on
// the select is fragile — naive-ui can fire update:value when the options
// prop identity churns, which would loop the stats endpoint. watch() only
// fires on real value changes, so programmatic and user-driven picks behave
// the same and options churn is ignored.
watch(customer, () => {
	loadStats()
})
</script>
