<template>
	<div class="flex flex-col gap-4" data-testid="soc-customers">
		<SocPanel title="Customers" caption="opened in the period · backlog now" flush>
			<div ref="tableBox" class="min-w-0">
				<n-data-table
					:columns
					:data="dashboard.customers"
					:row-key="(row: CustomerRow) => row.customer_code"
					size="small"
					:bordered="false"
					:scroll-x="1240"
					data-testid="customers-table"
				>
					<template #empty>
						<n-empty description="No customer activity in this period" class="py-6" />
					</template>
				</n-data-table>
			</div>
		</SocPanel>
	</div>
</template>

<script setup lang="tsx">
import type { DataTableColumns } from "naive-ui"
import type { CustomerRow, SocDashboard } from "@/types/soc-management"
import { NButton, NDataTable, NEmpty, NTooltip } from "naive-ui"
import { computed, useTemplateRef } from "vue"
import Icon from "@/components/common/Icon.vue"
import { usePinnedColumn } from "../composables/usePinnedColumn"
import ComplianceMeter from "../ui/ComplianceMeter.vue"
import SocPanel from "../ui/SocPanel.vue"
import { formatCount, formatDuration, oneLineTitle, TONE_COLOR } from "../utils"

const { dashboard } = defineProps<{ dashboard: SocDashboard }>()
const emit = defineEmits<{ (e: "focusCustomer", code: string): void }>()

const numeric = (value: number) => <span class="font-mono tabular-nums">{formatCount(value)}</span>

/** Below this width a pinned Customer column would eat the room the figures need to scroll in. */
const PIN_FROM_WIDTH = 500
const pinCustomer = usePinnedColumn(useTemplateRef<HTMLElement>("tableBox"), PIN_FROM_WIDTH)

const columns = computed<DataTableColumns<CustomerRow>>(() => [
	{
		title: oneLineTitle("Customer"),
		key: "customer_code",
		minWidth: 220,
		fixed: pinCustomer.value ? "left" : undefined,
		sorter: (a, b) => (a.customer_name ?? a.customer_code).localeCompare(b.customer_name ?? b.customer_code),
		render: row => (
			<div class="flex flex-col leading-tight">
				<span class="truncate font-medium">{row.customer_name ?? row.customer_code}</span>
				<span class="text-tertiary text-2xs font-mono">{row.customer_code}</span>
			</div>
		)
	},
	{
		title: oneLineTitle("Alerts"),
		key: "alerts",
		width: 90,
		align: "right",
		defaultSortOrder: "descend",
		sorter: (a, b) => a.alerts - b.alerts,
		render: row => numeric(row.alerts)
	},
	{
		title: oneLineTitle("Cases"),
		key: "cases",
		width: 80,
		align: "right",
		sorter: (a, b) => a.cases - b.cases,
		render: row => numeric(row.cases)
	},
	{
		title: oneLineTitle("Resolved"),
		key: "resolved",
		width: 104,
		align: "right",
		sorter: (a, b) => a.resolved - b.resolved,
		render: row => numeric(row.resolved)
	},
	{
		title: oneLineTitle("Open"),
		key: "open_now",
		width: 80,
		align: "right",
		sorter: (a, b) => a.open_now - b.open_now,
		render: row => numeric(row.open_now)
	},
	{
		title: oneLineTitle("Past SLA"),
		key: "breached_now",
		width: 104,
		align: "right",
		sorter: (a, b) => a.breached_now - b.breached_now,
		render: row => (
			<span
				class="font-mono tabular-nums"
				style={{ color: row.breached_now ? TONE_COLOR.bad : "var(--fg-tertiary-color)" }}
			>
				{row.breached_now}
			</span>
		)
	},
	{
		title: oneLineTitle("Alert SLA"),
		key: "alert_sla",
		minWidth: 160,
		sorter: (a, b) => (a.alert_sla.rate ?? -1) - (b.alert_sla.rate ?? -1),
		render: row => <ComplianceMeter compliance={row.alert_sla} label="Alerts resolved within SLA" />
	},
	{
		title: oneLineTitle("Case SLA"),
		key: "case_sla",
		minWidth: 160,
		sorter: (a, b) => (a.case_sla.rate ?? -1) - (b.case_sla.rate ?? -1),
		render: row => <ComplianceMeter compliance={row.case_sla} label="Cases resolved within SLA" />
	},
	{
		title: oneLineTitle("Median TTR"),
		key: "alert_ttr",
		width: 110,
		sorter: (a, b) => (a.alert_ttr.median ?? Infinity) - (b.alert_ttr.median ?? Infinity),
		render: row => <span class="font-mono tabular-nums">{formatDuration(row.alert_ttr.median)}</span>
	},
	{
		title: oneLineTitle("Top rule"),
		key: "top_rule",
		minWidth: 200,
		ellipsis: { tooltip: true },
		render: row => row.top_rule ?? <span class="text-tertiary">—</span>
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
							onClick={() => emit("focusCustomer", row.customer_code)}
							aria-label={`Focus on ${row.customer_code}`}
						>
							{{ icon: () => <Icon name="carbon:filter" /> }}
						</NButton>
					),
					default: () => "Show this customer only"
				}}
			</NTooltip>
		)
	}
])
</script>
