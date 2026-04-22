<template>
	<div class="feedback-dashboard @container flex flex-col gap-5">
		<!-- Customer picker -->
		<div class="flex flex-wrap items-center justify-between gap-3">
			<div class="flex items-center gap-2 text-sm">
				<span>Customer</span>
				<n-select
					v-model:value="customer"
					size="small"
					placeholder="Select a customer"
					:options="customerOptions"
					:show-checkmark="false"
					class="min-w-52"
					:disabled="loading || customerBootstrapLoading"
					@update:value="loadStats()"
				/>
			</div>
			<n-button size="small" :disabled="!customer || loading" @click="loadStats()">
				<template #icon>
					<Icon :name="RefreshIcon" :size="14" />
				</template>
				Refresh
			</n-button>
		</div>

		<n-spin :show="loading" class="min-h-40">
			<div v-if="!customer" class="pt-6 text-center">
				<n-empty description="Pick a customer to see their review feedback" />
			</div>

			<div v-else-if="stats" class="flex flex-col gap-5">
				<!-- Metric tiles -->
				<div class="grid grid-cols-1 gap-3 md:grid-cols-4">
					<MetricTile label="Total reviews" :value="stats.total_reviews.toString()" />
					<MetricTile
						label="Thumbs up"
						:value="pctLabel(stats.thumbs_up_pct)"
						:sub="`${stats.thumbs_up} up / ${stats.thumbs_down} down`"
						:color="pctColor(stats.thumbs_up_pct)"
					/>
					<MetricTile
						label="IOC verdict accuracy"
						:value="pctLabel(stats.ioc_accuracy.accuracy_pct)"
						:sub="`${stats.ioc_accuracy.correct}/${stats.ioc_accuracy.total} IOCs correct`"
						:color="pctColor(stats.ioc_accuracy.accuracy_pct)"
					/>
					<MetricTile
						label="Avg rating (overall)"
						:value="avgOverall == null ? '—' : `${avgOverall.toFixed(2)} / 5`"
						:sub="ratingSubtitle"
					/>
				</div>

				<!-- Template choice breakdown -->
				<CardEntity size="small" embedded>
					<template #headerMain>Template choice distribution</template>
					<template #default>
						<div class="flex flex-col gap-2">
							<TemplateChoiceBar
								label="Correct"
								color="success"
								:count="stats.template_choice_correct"
								:total="templateChoiceTotal"
							/>
							<TemplateChoiceBar
								label="Partial"
								color="warning"
								:count="stats.template_choice_partial"
								:total="templateChoiceTotal"
							/>
							<TemplateChoiceBar
								label="Wrong"
								color="danger"
								:count="stats.template_choice_wrong"
								:total="templateChoiceTotal"
							/>
							<div v-if="templateChoiceTotal === 0" class="text-secondary text-sm">
								No template choice feedback yet.
							</div>
						</div>
					</template>
				</CardEntity>

				<!-- Per-template table -->
				<CardEntity size="small" embedded>
					<template #headerMain>Per-template performance</template>
					<template #default>
						<n-empty
							v-if="!stats.per_template.length"
							description="No reviews yet"
							class="min-h-20 justify-center"
						/>
						<n-data-table
							v-else
							:columns="perTemplateColumns"
							:data="stats.per_template"
							:bordered="false"
							size="small"
							:row-key="(r: ReviewStatsTemplate) => r.template_used ?? '__null__'"
						/>
					</template>
				</CardEntity>

				<!-- Recent reviews -->
				<CardEntity size="small" embedded>
					<template #headerMain>Recent reviews</template>
					<template #default>
						<div v-if="!stats.recent_reviews.length" class="text-secondary text-sm">
							No reviews yet.
						</div>
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
import type {
	AiAnalystReview,
	AiAnalystReviewStats,
	ReviewStatsTemplate
} from "@/types/aiAnalyst.d"
import type { DataTableColumns } from "naive-ui"
import {
	NButton,
	NDataTable,
	NDrawer,
	NDrawerContent,
	NEmpty,
	NSelect,
	NSpin,
	useMessage
} from "naive-ui"
import { computed, onBeforeMount, ref } from "vue"
import Api from "@/api"
import Badge from "@/components/common/Badge.vue"
import CardEntity from "@/components/common/cards/CardEntity.vue"
import CardKV from "@/components/common/cards/CardKV.vue"
import Icon from "@/components/common/Icon.vue"
import { getApiErrorMessage } from "@/utils"
import { formatDate } from "@/utils/format"
import MetricTile from "./FeedbackMetricTile.vue"
import TemplateChoiceBar from "./FeedbackTemplateChoiceBar.vue"

const RefreshIcon = "carbon:renew"

const message = useMessage()

const customer = ref<string | null>(null)
const customerOptions = ref<{ label: string; value: string }[]>([])
const customerBootstrapLoading = ref(false)

const loading = ref(false)
const stats = ref<AiAnalystReviewStats | null>(null)

const showDrawer = ref(false)
const drawerReview = ref<AiAnalystReview | null>(null)

const templateChoiceTotal = computed(() =>
	stats.value
		? stats.value.template_choice_correct +
			stats.value.template_choice_partial +
			stats.value.template_choice_wrong
		: 0
)

// Composite avg across the three rubric axes — only counts axes with data.
const avgOverall = computed(() => {
	if (!stats.value) return null
	const parts = [
		stats.value.avg_rating_instructions,
		stats.value.avg_rating_artifacts,
		stats.value.avg_rating_severity
	].filter((v): v is number => v !== null)
	if (!parts.length) return null
	return parts.reduce((a, b) => a + b, 0) / parts.length
})

const ratingSubtitle = computed(() => {
	if (!stats.value) return ""
	const i = stats.value.avg_rating_instructions
	const a = stats.value.avg_rating_artifacts
	const s = stats.value.avg_rating_severity
	return `instr ${i ?? "—"} · artif ${a ?? "—"} · sev ${s ?? "—"}`
})

function pctLabel(pct: number | null): string {
	return pct === null || pct === undefined ? "—" : `${pct.toFixed(1)}%`
}
function pctColor(pct: number | null): "success" | "warning" | "danger" | undefined {
	if (pct === null) return undefined
	if (pct >= 75) return "success"
	if (pct >= 50) return "warning"
	return "danger"
}
function tplChoiceColor(choice: string): "success" | "warning" | "danger" | undefined {
	if (choice === "correct") return "success"
	if (choice === "partial") return "warning"
	if (choice === "wrong") return "danger"
	return undefined
}

const perTemplateColumns = computed<DataTableColumns<ReviewStatsTemplate>>(() => [
	{
		title: "Template",
		key: "template_used",
		render: row => row.template_used ?? "(none)"
	},
	{ title: "Total", key: "total", width: 80 },
	{
		title: "Up / Down",
		key: "verdict",
		width: 110,
		render: row => `${row.thumbs_up} / ${row.thumbs_down}`
	},
	{
		title: "C / P / W",
		key: "choice",
		width: 110,
		render: row => `${row.correct} / ${row.partial} / ${row.wrong}`
	},
	{
		title: "Instr",
		key: "avg_rating_instructions",
		width: 80,
		render: row => (row.avg_rating_instructions == null ? "—" : row.avg_rating_instructions.toFixed(2))
	},
	{
		title: "Artif",
		key: "avg_rating_artifacts",
		width: 80,
		render: row => (row.avg_rating_artifacts == null ? "—" : row.avg_rating_artifacts.toFixed(2))
	},
	{
		title: "Sev",
		key: "avg_rating_severity",
		width: 80,
		render: row => (row.avg_rating_severity == null ? "—" : row.avg_rating_severity.toFixed(2))
	}
])

function openDrawer(r: AiAnalystReview) {
	drawerReview.value = r
	showDrawer.value = true
}

async function bootstrapCustomers() {
	// Bootstrap customer picker off alerts_with_reports so we only list
	// customers that actually have AI runs — no external customer endpoint call.
	customerBootstrapLoading.value = true
	try {
		const res = await Api.aiAnalyst.getAlertsWithReports()
		if (res.data.success) {
			const codes = new Set((res.data.alerts || []).map(a => a.customer_code))
			customerOptions.value = Array.from(codes)
				.sort()
				.map(c => ({ label: c, value: c }))
			if (customerOptions.value.length && !customer.value) {
				customer.value = customerOptions.value[0].value
				await loadStats()
			}
		}
	} catch (err: unknown) {
		message.error(getApiErrorMessage(err as never) || "Failed to load customers")
	} finally {
		customerBootstrapLoading.value = false
	}
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

onBeforeMount(() => {
	bootstrapCustomers()
})
</script>
