<template>
	<div class="flex flex-col gap-4" data-testid="soc-rules">
		<div class="bg-border border-default grid grid-cols-1 gap-px overflow-hidden rounded-lg border sm:grid-cols-3">
			<KpiTile label="Rules firing" :value="formatCount(dashboard.rules.length)" hint="top 25 by alerts opened" />
			<KpiTile
				label="Noisy rules"
				:value="formatCount(noisy.length)"
				:tone="noisy.length ? 'warn' : 'neutral'"
				:hint="noisy.length ? `top: ${noisy[0].alert_name}` : 'none past the threshold'"
				help="A rule is noisy once at least five of its alerts were reviewed and half or more were judged false positives: a candidate for tuning."
			/>
			<KpiTile
				label="Converted to cases"
				:value="formatRate(dashboard.headline.case_conversion_rate)"
				hint="of all alerts opened in the period"
			/>
		</div>

		<SocPanel title="Detection rules" caption="by alerts opened in the period" flush>
			<template #actions>
				<n-checkbox v-model:checked="onlyNoisy" size="small" data-testid="rules-only-noisy">
					Noisy only
				</n-checkbox>
			</template>
			<n-data-table
				:columns
				:data="visible"
				:row-key="(row: RuleRow) => row.alert_name"
				size="small"
				:bordered="false"
				:scroll-x="1200"
				data-testid="rules-table"
			>
				<template #empty>
					<n-empty
						:description="onlyNoisy ? 'No noisy rule in this period' : 'No alert opened in this period'"
						class="py-6"
					/>
				</template>
			</n-data-table>
		</SocPanel>
	</div>
</template>

<script setup lang="tsx">
import type { DataTableColumns } from "naive-ui"
import type { RuleRow, SocDashboard } from "@/types/soc-management"
import { NButton, NCheckbox, NDataTable, NEmpty, NTag, NTooltip } from "naive-ui"
import { computed, shallowRef } from "vue"
import { useRouter } from "vue-router"
import Icon from "@/components/common/Icon.vue"
import ComplianceMeter from "../ui/ComplianceMeter.vue"
import KpiTile from "../ui/KpiTile.vue"
import SocPanel from "../ui/SocPanel.vue"
import Sparkline from "../ui/Sparkline.vue"
import { formatCount, formatDuration, formatRate, TONE_COLOR } from "../utils"

const { dashboard } = defineProps<{ dashboard: SocDashboard }>()

const router = useRouter()
const onlyNoisy = shallowRef(false)

const noisy = computed(() => dashboard.rules.filter(rule => rule.noisy))
const visible = computed(() => (onlyNoisy.value ? noisy.value : dashboard.rules))

/** The alert list, filtered to this rule — and to the one customer in scope, if there is one. */
function openAlerts(rule: RuleRow) {
	const codes = dashboard.customer_codes
	router.push({
		name: "IncidentManagement-Alerts",
		query: { title: rule.alert_name, ...(codes?.length === 1 ? { customerCode: codes[0] } : {}) }
	})
}

function falsePositive(row: RuleRow) {
	if (row.false_positive_rate == null) return <span class="text-tertiary font-mono">—</span>
	const color = row.noisy ? TONE_COLOR.bad : row.false_positive_rate >= 25 ? TONE_COLOR.warn : undefined
	return (
		<div class="flex flex-col leading-tight">
			<span class="font-mono tabular-nums" style={{ color }}>
				{formatRate(row.false_positive_rate)}
			</span>
			<span class="text-tertiary text-2xs font-mono">{`${row.false_positives} of ${row.reviewed} reviewed`}</span>
		</div>
	)
}

const columns: DataTableColumns<RuleRow> = [
	{
		title: "Rule",
		key: "alert_name",
		minWidth: 280,
		fixed: "left",
		render: row => (
			<div class="flex min-w-0 flex-col gap-1">
				<span class="truncate font-medium" title={row.alert_name}>
					{row.alert_name}
				</span>
				<div class="flex flex-wrap items-center gap-1">
					{row.sources.map(source => (
						<NTag key={source} size="tiny" bordered={false} class="font-mono">
							{source}
						</NTag>
					))}
					{row.noisy ? (
						<NTag size="tiny" type="warning" bordered={false} round>
							{{ default: () => "noisy", icon: () => <Icon name="carbon:volume-up" size={11} /> }}
						</NTag>
					) : null}
				</div>
			</div>
		)
	},
	{
		title: "Alerts",
		key: "alerts",
		width: 170,
		defaultSortOrder: "descend",
		sorter: (a, b) => a.alerts - b.alerts,
		render: row => (
			<div class="flex items-center gap-3">
				<span class="w-10 text-right font-mono tabular-nums">{formatCount(row.alerts)}</span>
				<Sparkline values={row.series} />
			</div>
		)
	},
	{
		title: "In a case",
		key: "in_case",
		width: 100,
		sorter: (a, b) => a.in_case - b.in_case,
		render: row => (
			<div class="flex flex-col leading-tight">
				<span class="font-mono tabular-nums">{formatCount(row.in_case)}</span>
				<span class="text-tertiary text-2xs font-mono">
					{formatRate(row.alerts ? (row.in_case * 100) / row.alerts : null)}
				</span>
			</div>
		)
	},
	{
		title: "False positive",
		key: "false_positive_rate",
		width: 130,
		sorter: (a, b) => (a.false_positive_rate ?? -1) - (b.false_positive_rate ?? -1),
		render: falsePositive
	},
	{
		title: "Median TTR",
		key: "ttr",
		width: 110,
		sorter: (a, b) => (a.ttr.median ?? Infinity) - (b.ttr.median ?? Infinity),
		render: row => <span class="font-mono tabular-nums">{formatDuration(row.ttr.median)}</span>
	},
	{
		title: "Resolved in SLA",
		key: "sla",
		minWidth: 160,
		render: row => <ComplianceMeter compliance={row.sla} label="Resolved within SLA" />
	},
	{
		title: "Open",
		key: "open_now",
		width: 70,
		align: "right",
		sorter: (a, b) => a.open_now - b.open_now,
		render: row => <span class="font-mono tabular-nums">{row.open_now}</span>
	},
	{
		title: "",
		key: "actions",
		width: 56,
		align: "right",
		render: row => (
			<NTooltip>
				{{
					trigger: () => (
						<NButton
							size="tiny"
							quaternary
							onClick={() => openAlerts(row)}
							aria-label={`Open the alerts of ${row.alert_name}`}
						>
							{{ icon: () => <Icon name="carbon:launch" /> }}
						</NButton>
					),
					default: () => "Open these alerts"
				}}
			</NTooltip>
		)
	}
]
</script>
