<template>
	<div class="flex flex-col gap-4" data-testid="soc-workload">
		<div
			class="bg-border border-default grid grid-cols-1 gap-px overflow-hidden rounded-lg border sm:grid-cols-2 xl:grid-cols-5"
		>
			<KpiTile
				label="Open now"
				:value="formatCount(workload.open_alerts + workload.open_cases)"
				:hint="`${formatCount(workload.open_alerts)} alerts · ${formatCount(workload.open_cases)} cases`"
			/>
			<KpiTile
				label="Unassigned"
				:value="formatCount(workload.unassigned_alerts + workload.unassigned_cases)"
				:tone="workload.unassigned_alerts + workload.unassigned_cases ? 'warn' : 'neutral'"
				:hint="oldestUnassigned"
			/>
			<KpiTile
				label="At risk"
				:value="formatCount(workload.at_risk)"
				:tone="workload.at_risk ? 'warn' : 'neutral'"
				hint="last quarter of a clock"
			/>
			<KpiTile
				label="Past SLA"
				:value="formatCount(workload.breached)"
				:tone="workload.breached ? 'bad' : 'good'"
				hint="a running clock ran out"
			/>
			<KpiTile
				label="Waiting on customer"
				:value="formatCount(workload.waiting_on_customer)"
				hint="clocks stopped until they reply"
				help="Open items set to Waiting on customer. Their SLA clocks are stopped, and the customer's reply hands them back to the SOC."
				test-id="kpi-waiting"
			/>
		</div>

		<div class="grid gap-4 xl:grid-cols-2">
			<SocPanel title="Backlog by severity" caption="open now">
				<LoadBars :rows="severityRows" :label-dot="row => colors.severity(row.label)" />
			</SocPanel>
			<SocPanel
				:title="dashboard.viewer.sees_all_analysts ? 'Backlog by assignee' : 'Your backlog'"
				:caption="
					dashboard.viewer.sees_all_analysts ? 'open now' : 'other assignees are visible to administrators'
				"
			>
				<LoadBars :rows="assigneeRows" empty-text="Nothing open is assigned" />
			</SocPanel>
		</div>

		<SocPanel title="Needs attention" :caption="`${formatCount(total)} open item(s) past or near SLA`" flush>
			<template #actions>
				<SegmentedToggle
					v-model="entityFilter"
					:options="ENTITY_OPTIONS"
					label="Show"
					test-id="attention-entity"
				/>
				<SegmentedToggle
					v-model="stateFilter"
					:options="STATE_OPTIONS"
					label="SLA state"
					test-id="attention-state"
				/>
			</template>
			<n-alert v-if="error" type="error" :bordered="false" class="m-3">
				Could not load the list: {{ errorText }}
			</n-alert>
			<n-spin v-else :show="loading">
				<AttentionList :items />
				<p v-if="total > items.length" class="text-tertiary m-0 px-3 py-2 text-xs">
					Showing the {{ items.length }} most urgent of {{ total }}.
				</p>
			</n-spin>
		</SocPanel>
	</div>
</template>

<script setup lang="ts">
import type { LoadRow } from "../ui/LoadBars.vue"
import type { SocScopeQuery } from "@/api/endpoints/soc-management"
import type { SlaEntity, SocDashboard } from "@/types/soc-management"
import { NAlert, NSpin } from "naive-ui"
import { computed, shallowRef } from "vue"
import SegmentedToggle from "@/components/common/SegmentedToggle.vue"
import AttentionList from "../AttentionList.vue"
import { useResolvedColors } from "../charts/chart-colors"
import { useAttention } from "../composables/useAttention"
import KpiTile from "../ui/KpiTile.vue"
import LoadBars from "../ui/LoadBars.vue"
import SocPanel from "../ui/SocPanel.vue"
import { formatCount, formatDuration, parseUtc } from "../utils"

const { dashboard, scope } = defineProps<{ dashboard: SocDashboard; scope: SocScopeQuery }>()

const colors = useResolvedColors()
const workload = computed(() => dashboard.workload)
const ENTITY_OPTIONS: { value: SlaEntity | "all"; label: string }[] = [
	{ value: "all", label: "All" },
	{ value: "alert", label: "Alerts" },
	{ value: "case", label: "Cases" }
]
const STATE_OPTIONS: { value: "breached" | "at_risk" | "all"; label: string }[] = [
	{ value: "all", label: "Any" },
	{ value: "breached", label: "Past SLA" },
	{ value: "at_risk", label: "At risk" }
]
const entityFilter = shallowRef<SlaEntity | "all">("all")
const stateFilter = shallowRef<"breached" | "at_risk" | "all">("all")

const { items, total, loading, error } = useAttention(
	computed(() => scope),
	computed(() => ({
		entity: entityFilter.value === "all" ? undefined : entityFilter.value,
		state: stateFilter.value === "all" ? undefined : stateFilter.value
	}))
)

const errorText = computed(() => {
	const err = error.value as { response?: { data?: { detail?: string } }; message?: string } | null
	return err?.response?.data?.detail ?? err?.message ?? "unknown error"
})

const oldestUnassigned = computed(() => {
	const oldest = parseUtc(workload.value.oldest_unassigned_at)
	if (!oldest) return "the queue is empty"
	return `oldest waiting ${formatDuration((Date.now() - oldest.valueOf()) / 1000)}`
})

const severityRows = computed<LoadRow[]>(() =>
	workload.value.by_severity.map(row => ({ key: row.severity, label: row.severity, ...row }))
)
const assigneeRows = computed<LoadRow[]>(() =>
	workload.value.by_assignee.map(row => ({ key: row.username, label: row.username, ...row }))
)
</script>
