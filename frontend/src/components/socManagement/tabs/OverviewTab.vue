<template>
	<div class="flex flex-col gap-4" data-testid="soc-overview">
		<!-- Hero band: the one number (resolution SLA) and the six figures around it. -->
		<section class="hero-band border-default overflow-hidden rounded-lg border">
			<div class="grid lg:grid-cols-[280px_minmax(0,1fr)]">
				<div
					class="hero-gauge border-default flex flex-col items-center justify-center gap-3 border-b p-6 lg:border-r lg:border-b-0"
				>
					<SlaGauge :rate="alerts.sla.resolve.rate" label="Resolved in SLA" />
					<DeltaChip :delta="computePointDelta(alerts.sla.resolve.rate, previous.alerts.sla.resolve.rate)" />
					<dl class="m-0 grid w-full grid-cols-2 gap-2 text-center">
						<div class="flex flex-col gap-0.5">
							<dt :class="SECTION_LABEL" class="text-2xs!">Response</dt>
							<dd
								class="m-0 font-mono text-sm"
								:style="{ color: TONE_COLOR[rateTone(alerts.sla.ack.rate)] }"
							>
								{{ formatRate(alerts.sla.ack.rate) }}
							</dd>
						</div>
						<div class="flex flex-col gap-0.5">
							<dt :class="SECTION_LABEL" class="text-2xs!">Cases</dt>
							<dd
								class="m-0 font-mono text-sm"
								:style="{ color: TONE_COLOR[rateTone(cases.sla.resolve.rate)] }"
							>
								{{ formatRate(cases.sla.resolve.rate) }}
							</dd>
						</div>
					</dl>
				</div>
				<div class="bg-border grid grid-cols-1 gap-px sm:grid-cols-2 xl:grid-cols-3">
					<KpiTile
						label="Alerts opened"
						:value="formatCount(alerts.opened)"
						:delta="computeDelta(alerts.opened, previous.alerts.opened)"
						:hint="`${formatCount(alerts.resolved)} resolved in the period`"
						test-id="kpi-alerts-opened"
					/>
					<KpiTile
						label="Cases opened"
						:value="formatCount(cases.opened)"
						:delta="computeDelta(cases.opened, previous.cases.opened)"
						:hint="`${formatCount(cases.resolved)} resolved in the period`"
						test-id="kpi-cases-opened"
					/>
					<KpiTile
						label="Time to acknowledge"
						:value="formatDuration(alerts.tta.median)"
						:delta="computeDelta(alerts.tta.median, previous.alerts.tta.median, 'down')"
						:hint="`median · p90 ${formatDuration(alerts.tta.p90)} · mean ${formatDuration(alerts.tta.mean)}`"
						help="From the alert reaching CoPilot to the first SOC action on it: an assignment, a status change, a comment, a verdict, an escalation or a case link."
						test-id="kpi-tta"
					/>
					<KpiTile
						label="Time to resolve"
						:value="formatDuration(alerts.ttr.median)"
						:delta="computeDelta(alerts.ttr.median, previous.alerts.ttr.median, 'down')"
						:hint="`median · p90 ${formatDuration(alerts.ttr.p90)} · mean ${formatDuration(alerts.ttr.mean)}`"
						help="From the alert reaching CoPilot to it being closed. Medians are robust to one bulk close of old noise; the mean and p90 show the tail."
						test-id="kpi-ttr"
					/>
					<KpiTile
						label="Past SLA now"
						:value="formatCount(dashboard.workload.breached)"
						:tone="dashboard.workload.breached ? 'bad' : 'good'"
						:hint="breachedHint"
						help="Open alerts and cases whose response or resolution clock has run out and is still running."
						test-id="kpi-breached"
					/>
					<KpiTile
						label="False positive rate"
						:value="formatRate(headline.false_positive_rate)"
						:delta="computePointDelta(headline.false_positive_rate, previous.false_positive_rate)"
						:hint="`of ${formatCount(headline.reviewed_alerts)} reviewed · ${formatRate(headline.case_conversion_rate)} became cases`"
						help="Share of reviewed alerts judged false positives — of the alerts that were triaged, never of everything ingested."
						test-id="kpi-fp-rate"
					/>
				</div>
			</div>
		</section>

		<div class="grid gap-4 xl:grid-cols-5">
			<SocPanel
				title="Volume"
				:caption="`opened vs resolved · per ${dashboard.period.bucket}`"
				class="xl:col-span-3"
			>
				<template #actions>
					<n-radio-group v-model:value="volumeEntity" size="small">
						<n-radio-button value="alert">Alerts</n-radio-button>
						<n-radio-button value="case">Cases</n-radio-button>
					</n-radio-group>
				</template>
				<VolumeTrendChart
					:points="dashboard.trends"
					:bucket="dashboard.period.bucket"
					:entity="volumeEntity"
					:height="290"
				/>
			</SocPanel>

			<SocPanel title="Needs attention" :caption="attentionCaption" flush class="xl:col-span-2">
				<template #actions>
					<n-button size="tiny" quaternary @click="emit('openTab', 'workload')">
						View all
						<template #icon><Icon name="carbon:arrow-right" /></template>
					</n-button>
				</template>
				<n-scrollbar trigger="none" class="max-h-[340px]" data-testid="overview-attention-scroll">
					<AttentionList :items="dashboard.attention" />
				</n-scrollbar>
			</SocPanel>
		</div>

		<div class="grid gap-4 xl:grid-cols-2">
			<SocPanel title="Resolution SLA over time" :caption="`by opening date · objective ${RATE_GOOD}%`">
				<ComplianceTrendChart :points="dashboard.trends" :bucket="dashboard.period.bucket" />
			</SocPanel>
			<SocPanel title="Alerts by severity" caption="opened in the period" flush>
				<template #actions>
					<n-button size="tiny" quaternary @click="emit('openTab', 'sla')">
						SLA detail
						<template #icon><Icon name="carbon:arrow-right" /></template>
					</n-button>
				</template>
				<n-data-table
					:columns="severityColumns"
					:data="alertSeverities"
					:row-key="(row: SeverityRow) => row.severity"
					size="small"
					:bordered="false"
					:scroll-x="620"
					data-testid="overview-severity-table"
				/>
			</SocPanel>
		</div>
	</div>
</template>

<script setup lang="tsx">
import type { DataTableColumns } from "naive-ui"
import type { SocTab } from "../composables/useSocFilters"
import type { SeverityRow, SlaEntity, SocDashboard } from "@/types/soc-management"
import { NButton, NDataTable, NRadioButton, NRadioGroup, NScrollbar } from "naive-ui"
import { computed, shallowRef } from "vue"
import Icon from "@/components/common/Icon.vue"
import { SECTION_LABEL } from "@/components/common/section-label"
import AttentionList from "../AttentionList.vue"
import ComplianceTrendChart from "../charts/ComplianceTrendChart.vue"
import VolumeTrendChart from "../charts/VolumeTrendChart.vue"
import ComplianceMeter from "../ui/ComplianceMeter.vue"
import DeltaChip from "../ui/DeltaChip.vue"
import KpiTile from "../ui/KpiTile.vue"
import SeverityTag from "../ui/SeverityTag.vue"
import SlaGauge from "../ui/SlaGauge.vue"
import SocPanel from "../ui/SocPanel.vue"
import {
	computeDelta,
	computePointDelta,
	formatCount,
	formatDuration,
	formatRate,
	RATE_GOOD,
	rateTone,
	TONE_COLOR
} from "../utils"

const { dashboard } = defineProps<{ dashboard: SocDashboard }>()
const emit = defineEmits<{ (e: "openTab", tab: SocTab): void }>()

const volumeEntity = shallowRef<SlaEntity>("alert")

const headline = computed(() => dashboard.headline)
const previous = computed(() => dashboard.previous)
const alerts = computed(() => dashboard.headline.alerts)
const cases = computed(() => dashboard.headline.cases)
const openItems = computed(() => dashboard.workload.open_alerts + dashboard.workload.open_cases)
const breachedHint = computed(() => {
	const { at_risk, waiting_on_customer } = dashboard.workload
	const waiting = waiting_on_customer ? ` · ${formatCount(waiting_on_customer)} waiting` : ""
	return `${formatCount(at_risk)} at risk · ${formatCount(openItems.value)} open${waiting}`
})
const alertSeverities = computed(() => dashboard.severities.filter(row => row.entity === "alert"))
const severityColumns: DataTableColumns<SeverityRow> = [
	{ title: "Severity", key: "severity", width: 130, render: row => <SeverityTag severity={row.severity} /> },
	{
		title: "Opened",
		key: "opened",
		width: 90,
		align: "right",
		render: row => <span class="font-mono tabular-nums">{formatCount(row.opened)}</span>
	},
	{
		title: "Response",
		key: "ack",
		minWidth: 150,
		render: row => <ComplianceMeter compliance={row.sla.ack} label="Acknowledged within SLA" compact />
	},
	{
		title: "Resolution",
		key: "resolve",
		minWidth: 150,
		render: row => <ComplianceMeter compliance={row.sla.resolve} label="Resolved within SLA" compact />
	},
	{
		title: "Past SLA",
		key: "breached_now",
		width: 90,
		align: "right",
		render: row => (
			<span
				class="font-mono tabular-nums"
				style={{ color: row.breached_now ? TONE_COLOR.bad : "var(--fg-tertiary-color)" }}
			>
				{row.breached_now}
			</span>
		)
	}
]
const attentionCaption = computed(() => {
	const { breached, at_risk } = dashboard.workload
	return `${breached} past SLA · ${at_risk} at risk`
})
</script>

<style scoped>
.hero-band {
	background-color: var(--bg-default-color);
}

.hero-gauge {
	background: radial-gradient(circle at 50% 40%, rgb(var(--primary-color-rgb) / 0.07), transparent 65%);
}
</style>
