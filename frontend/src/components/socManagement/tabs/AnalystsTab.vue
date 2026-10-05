<template>
	<div class="flex flex-col gap-4" data-testid="soc-analysts">
		<n-alert
			v-if="!dashboard.viewer.sees_all_analysts"
			type="info"
			:bordered="false"
			data-testid="analysts-own-only"
		>
			You are seeing your own figures. The comparison across analysts is visible to administrators.
		</n-alert>

		<SocPanel
			:title="dashboard.viewer.sees_all_analysts ? 'Analyst performance' : 'Your performance'"
			caption="activity in the period · workload now"
			flush
		>
			<div ref="tableBox" class="min-w-0">
				<n-data-table
					:columns
					:data="dashboard.analysts"
					:row-key="(row: AnalystRow) => row.username"
					size="small"
					:bordered="false"
					:scroll-x="1400"
					data-testid="analysts-table"
				>
					<template #empty>
						<n-empty description="No SOC activity in this period" class="py-6" />
					</template>
				</n-data-table>
			</div>
		</SocPanel>

		<p class="text-tertiary m-0 text-xs leading-relaxed">
			Work is credited to whoever did it: the first SOC response to an item, and its closure. A closure by a
			customer resolves the item but is no analyst's work, so it is left out here. Times are medians.
		</p>
	</div>
</template>

<script setup lang="tsx">
import type { DataTableColumns } from "naive-ui"
import type { AnalystRow, SocDashboard } from "@/types/soc-management"
import { NAlert, NAvatar, NDataTable, NEmpty } from "naive-ui"
import { computed, useTemplateRef } from "vue"
import { getAvatar } from "@/utils"
import { usePinnedColumn } from "../composables/usePinnedColumn"
import ComplianceMeter from "../ui/ComplianceMeter.vue"
import SocPanel from "../ui/SocPanel.vue"
import { formatCount, formatDuration, oneLineTitle, TONE_COLOR } from "../utils"

const { dashboard } = defineProps<{ dashboard: SocDashboard }>()

/** "jane.doe" → JD, "e2e_sla_bob" → EB: first and last part, so a shared prefix still tells people apart. */
function initials(username: string) {
	const parts = username.split(/[\s._-]+/).filter(Boolean)
	const first = parts[0]?.[0] ?? "?"
	const last = parts.length > 1 ? parts[parts.length - 1][0] : (parts[0]?.[1] ?? "")
	return `${first}${last}`.toUpperCase()
}

/** The analyst's oreo avatar, drawn once per username: the same person keeps the same face. */
const avatars = new Map<string, string>()
function avatarOf(username: string) {
	let avatar = avatars.get(username)
	if (!avatar) {
		avatar = getAvatar({ seed: username, text: initials(username), size: 56 })
		avatars.set(username, avatar)
	}
	return avatar
}

function count(value: number, muted = false) {
	return <span class={["font-mono tabular-nums", muted && !value ? "text-tertiary" : ""]}>{formatCount(value)}</span>
}

function load(value: number, tone: "bad" | "warn") {
	return (
		<span class="font-mono tabular-nums" style={{ color: value ? TONE_COLOR[tone] : "var(--fg-tertiary-color)" }}>
			{value}
		</span>
	)
}

/** Below this width a pinned Analyst column would eat the room the figures need to scroll in. */
const PIN_FROM_WIDTH = 500
const pinAnalyst = usePinnedColumn(useTemplateRef<HTMLElement>("tableBox"), PIN_FROM_WIDTH)

const columns = computed<DataTableColumns<AnalystRow>>(() => [
	{
		title: oneLineTitle("Analyst"),
		key: "username",
		width: 190,
		fixed: pinAnalyst.value ? "left" : undefined,
		sorter: (a, b) => a.username.localeCompare(b.username),
		render: row => (
			<div class="flex items-center gap-2">
				<NAvatar
					round
					size={28}
					src={avatarOf(row.username)}
					class="analyst-avatar shrink-0"
					imgProps={{ alt: `${row.username} avatar` }}
					data-testid={`analyst-avatar-${row.username}`}
				/>
				<span class="truncate font-medium">{row.username}</span>
			</div>
		)
	},
	{
		title: oneLineTitle("Acknowledged"),
		key: "acknowledged",
		width: 140,
		align: "right",
		sorter: (a, b) => a.alerts_acknowledged + a.cases_acknowledged - (b.alerts_acknowledged + b.cases_acknowledged),
		render: row => count(row.alerts_acknowledged + row.cases_acknowledged)
	},
	{
		title: oneLineTitle("Alerts closed"),
		key: "alerts_resolved",
		width: 130,
		align: "right",
		defaultSortOrder: "descend",
		sorter: (a, b) => a.alerts_resolved - b.alerts_resolved,
		render: row => count(row.alerts_resolved)
	},
	{
		title: oneLineTitle("Cases closed"),
		key: "cases_resolved",
		width: 130,
		align: "right",
		sorter: (a, b) => a.cases_resolved - b.cases_resolved,
		render: row => count(row.cases_resolved, true)
	},
	{
		title: oneLineTitle("Median TTA"),
		key: "tta",
		width: 130,
		sorter: (a, b) => (a.tta.median ?? Infinity) - (b.tta.median ?? Infinity),
		render: row => <span class="font-mono tabular-nums">{formatDuration(row.tta.median)}</span>
	},
	{
		title: oneLineTitle("Median TTR"),
		key: "ttr",
		width: 130,
		sorter: (a, b) => (a.ttr.median ?? Infinity) - (b.ttr.median ?? Infinity),
		render: row => <span class="font-mono tabular-nums">{formatDuration(row.ttr.median)}</span>
	},
	{
		title: oneLineTitle("Resolved in SLA"),
		key: "sla",
		minWidth: 170,
		sorter: (a, b) => (a.sla.rate ?? -1) - (b.sla.rate ?? -1),
		render: row => <ComplianceMeter compliance={row.sla} label="Of the items they closed, resolved within SLA" />
	},
	{
		title: oneLineTitle("Open now"),
		key: "open",
		width: 160,
		sorter: (a, b) => a.open_alerts + a.open_cases - (b.open_alerts + b.open_cases),
		render: row => (
			<span class="font-mono text-xs whitespace-nowrap tabular-nums">{`${row.open_alerts} alerts · ${row.open_cases} cases`}</span>
		)
	},
	{
		title: oneLineTitle("At risk"),
		key: "at_risk",
		width: 100,
		align: "right",
		sorter: (a, b) => a.at_risk - b.at_risk,
		render: row => load(row.at_risk, "warn")
	},
	{
		title: oneLineTitle("Past SLA"),
		key: "breached",
		width: 110,
		align: "right",
		sorter: (a, b) => a.breached - b.breached,
		render: row => load(row.breached, "bad")
	}
])
</script>
