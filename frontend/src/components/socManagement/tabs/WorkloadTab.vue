<template>
	<div class="flex flex-col gap-4" data-testid="soc-workload">
		<div
			class="bg-border border-default grid grid-cols-1 gap-px overflow-hidden rounded-lg border sm:grid-cols-2 xl:grid-cols-4"
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
		</div>

		<div class="grid gap-4 xl:grid-cols-2">
			<SocPanel title="Backlog by severity" caption="open now">
				<LoadBars :rows="severityRows">
					<template #label="{ row }">
						<SeverityTag :severity="row.label as Severity" />
					</template>
				</LoadBars>
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
				<n-radio-group v-model:value="entityFilter" size="small" data-testid="attention-entity">
					<n-radio-button value="all">All</n-radio-button>
					<n-radio-button value="alert">Alerts</n-radio-button>
					<n-radio-button value="case">Cases</n-radio-button>
				</n-radio-group>
				<n-radio-group v-model:value="stateFilter" size="small" data-testid="attention-state">
					<n-radio-button value="all">Any</n-radio-button>
					<n-radio-button value="breached">Past SLA</n-radio-button>
					<n-radio-button value="at_risk">At risk</n-radio-button>
				</n-radio-group>
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
import type { Severity, SlaEntity, SocDashboard } from "@/types/soc-management"
import { NAlert, NRadioButton, NRadioGroup, NSpin } from "naive-ui"
import { computed, shallowRef } from "vue"
import AttentionList from "../AttentionList.vue"
import { useAttention } from "../composables/useAttention"
import KpiTile from "../ui/KpiTile.vue"
import LoadBars from "../ui/LoadBars.vue"
import SeverityTag from "../ui/SeverityTag.vue"
import SocPanel from "../ui/SocPanel.vue"
import { formatCount, formatDuration, parseUtc } from "../utils"

const { dashboard, scope } = defineProps<{ dashboard: SocDashboard; scope: SocScopeQuery }>()

const workload = computed(() => dashboard.workload)
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
