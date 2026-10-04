<template>
	<div class="flex flex-col gap-4" data-testid="soc-sla">
		<div class="flex flex-wrap items-center justify-between gap-3">
			<n-radio-group v-model:value="entity" size="small" data-testid="sla-entity">
				<n-radio-button value="alert">Alerts</n-radio-button>
				<n-radio-button value="case">Cases</n-radio-button>
			</n-radio-group>
			<span class="text-tertiary font-mono text-xs">targets: {{ policyScope }}</span>
		</div>

		<div
			class="bg-border border-default grid grid-cols-1 gap-px overflow-hidden rounded-lg border sm:grid-cols-2 xl:grid-cols-4"
		>
			<KpiTile
				label="Acknowledged in SLA"
				:value="formatRate(current.sla.ack.rate)"
				:tone="rateTone(current.sla.ack.rate)"
				:delta="computePointDelta(current.sla.ack.rate, before.sla.ack.rate)"
				:hint="complianceSummary(current.sla.ack)"
			/>
			<KpiTile
				label="Resolved in SLA"
				:value="formatRate(current.sla.resolve.rate)"
				:tone="rateTone(current.sla.resolve.rate)"
				:delta="computePointDelta(current.sla.resolve.rate, before.sla.resolve.rate)"
				:hint="complianceSummary(current.sla.resolve)"
			/>
			<KpiTile
				label="Time to acknowledge"
				:value="formatDuration(current.tta.median)"
				:delta="computeDelta(current.tta.median, before.tta.median, 'down')"
				:hint="`median · p90 ${formatDuration(current.tta.p90)} · ${current.tta.count} measured`"
			/>
			<KpiTile
				label="Time to resolve"
				:value="formatDuration(current.ttr.median)"
				:delta="computeDelta(current.ttr.median, before.ttr.median, 'down')"
				:hint="`median · p90 ${formatDuration(current.ttr.p90)} · ${current.ttr.count} measured`"
			/>
		</div>

		<SocPanel :title="`${entity === 'alert' ? 'Alerts' : 'Cases'} by severity`" caption="target vs actual" flush>
			<n-data-table
				:columns
				:data="rows"
				:row-key="(row: SeverityRow) => row.severity"
				size="small"
				:bordered="false"
				:scroll-x="1180"
				data-testid="sla-severity-table"
			/>
		</SocPanel>

		<div class="grid gap-4 xl:grid-cols-3">
			<SocPanel
				title="Resolution SLA over time"
				:caption="`alerts + cases · objective ${RATE_GOOD}%`"
				class="xl:col-span-2"
			>
				<ComplianceTrendChart :points="dashboard.trends" :bucket="dashboard.period.bucket" />
			</SocPanel>
			<SocPanel title="How it is measured">
				<ul class="text-secondary m-0 flex list-none flex-col gap-2.5 p-0 text-xs leading-relaxed">
					<li>
						<b class="text-default">Clocks start</b>
						when an item reaches CoPilot — an alert re-firing while open does not restart it.
					</li>
					<li>
						<b class="text-default">Acknowledged</b>
						is the first SOC action: assignment, status change, comment, verdict, escalation or case link.
						Customers and automation never acknowledge.
					</li>
					<li>
						<b class="text-default">Compliance</b>
						counts items whose outcome is known: met ÷ (met + breached). Items still on track are left out.
					</li>
					<li>
						<b class="text-default">Targets</b>
						are those in force when the item opened; a later policy change applies to open items only on
						request.
					</li>
					<li v-if="dashboard.tracking_since">
						<b class="text-default">Tracking began</b>
						{{ trackingSince }}; older items count in volumes only.
					</li>
				</ul>
			</SocPanel>
		</div>
	</div>
</template>

<script setup lang="tsx">
import type { DataTableColumns } from "naive-ui"
import type { SeverityRow, SlaEntity, SocDashboard } from "@/types/soc-management"
import { NDataTable, NRadioButton, NRadioGroup } from "naive-ui"
import { computed, shallowRef } from "vue"
import ComplianceTrendChart from "../charts/ComplianceTrendChart.vue"
import ComplianceMeter from "../ui/ComplianceMeter.vue"
import DurationCell from "../ui/DurationCell.vue"
import KpiTile from "../ui/KpiTile.vue"
import SeverityTag from "../ui/SeverityTag.vue"
import SocPanel from "../ui/SocPanel.vue"
import TargetCell from "../ui/TargetCell.vue"
import {
	complianceSummary,
	computeDelta,
	computePointDelta,
	formatCount,
	formatDuration,
	formatRate,
	parseUtc,
	RATE_GOOD,
	rateTone,
	TONE_COLOR
} from "../utils"

const { dashboard } = defineProps<{ dashboard: SocDashboard }>()

const entity = shallowRef<SlaEntity>("alert")

const current = computed(() => (entity.value === "alert" ? dashboard.headline.alerts : dashboard.headline.cases))
const before = computed(() => (entity.value === "alert" ? dashboard.previous.alerts : dashboard.previous.cases))
const rows = computed(() => dashboard.severities.filter(row => row.entity === entity.value))
const targets = computed(
	() =>
		new Map(dashboard.policy.cells.filter(cell => cell.entity === entity.value).map(cell => [cell.severity, cell]))
)
const policyScope = computed(() =>
	dashboard.policy.customer_code ? `${dashboard.policy.customer_code} policy` : "global policy"
)
const trackingSince = computed(() => parseUtc(dashboard.tracking_since)?.local().format("D MMM YYYY") ?? "")

/** A column title that stays on one line, however narrow the table gets. */
const oneLine = (title: string) => () => <span class="whitespace-nowrap">{title}</span>

const columns = computed<DataTableColumns<SeverityRow>>(() => [
	{
		title: "Severity",
		key: "severity",
		width: 140,
		fixed: "left",
		render: row => <SeverityTag severity={row.severity} />
	},
	{
		title: oneLine("Response target"),
		key: "ack_target",
		width: 150,
		render: row => <TargetCell minutes={targets.value.get(row.severity)?.ack_minutes} />
	},
	{
		title: oneLine("Resolution target"),
		key: "resolve_target",
		width: 160,
		render: row => <TargetCell minutes={targets.value.get(row.severity)?.resolve_minutes} />
	},
	{
		title: "Opened",
		key: "opened",
		width: 80,
		align: "right",
		render: row => <span class="font-mono tabular-nums">{formatCount(row.opened)}</span>
	},
	{
		title: oneLine("Median TTA"),
		key: "tta",
		width: 120,
		align: "right",
		render: row => <DurationCell stats={row.tta} />
	},
	{
		title: "Acknowledged in SLA",
		key: "ack",
		minWidth: 170,
		render: row => <ComplianceMeter compliance={row.sla.ack} label="Acknowledged within SLA" />
	},
	{
		title: oneLine("Median TTR"),
		key: "ttr",
		width: 120,
		align: "right",
		render: row => <DurationCell stats={row.ttr} />
	},
	{
		title: "Resolved in SLA",
		key: "resolve",
		minWidth: 170,
		render: row => <ComplianceMeter compliance={row.sla.resolve} label="Resolved within SLA" />
	},
	{
		title: "Open",
		key: "open_now",
		width: 70,
		align: "right",
		render: row => <span class="font-mono tabular-nums">{formatCount(row.open_now)}</span>
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
])
</script>
