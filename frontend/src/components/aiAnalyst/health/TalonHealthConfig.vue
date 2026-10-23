<template>
	<div class="grid grid-cols-1 gap-x-8 gap-y-5 md:grid-cols-2 xl:grid-cols-4" data-testid="talon-health-config">
		<section class="flex flex-col gap-2">
			<span :class="SECTION_LABEL">Write-back</span>
			<div class="flex items-center justify-between gap-2 text-sm">
				<span class="text-secondary">Mode</span>
				<b data-testid="talon-config-writeback">
					<bdi>{{ formatWriteback(config.writeback_mode) }}</bdi>
				</b>
			</div>
			<div class="flex flex-col gap-1 text-sm">
				<span class="text-secondary">
					Live customers
					<span v-if="scope === 'assigned'" class="text-tertiary text-xs">(only yours are listed)</span>
				</span>
				<div v-if="liveCustomers.length" class="flex flex-wrap gap-1" data-testid="talon-config-live">
					<n-tag v-for="code of liveCustomers" :key="code" size="small" :bordered="false">
						<bdi>{{ code }}</bdi>
					</n-tag>
				</div>
				<span v-else class="text-tertiary text-xs" data-testid="talon-config-live-none">
					{{ scope === "assigned" ? "None of your customers" : "None" }}
				</span>
			</div>
		</section>

		<section class="flex flex-col gap-2">
			<span :class="SECTION_LABEL">Automation</span>
			<div class="flex items-center justify-between gap-2 text-sm">
				<span class="text-secondary">Highest level</span>
				<b data-testid="talon-config-automation">{{ automationLevel }}</b>
			</div>
			<div class="flex items-center justify-between gap-2 text-sm">
				<span class="text-secondary">Policy source</span>
				<span>
					<bdi>{{ config.automation_policy_source ?? "Not reported" }}</bdi>
				</span>
			</div>
			<span :class="SECTION_LABEL" class="mt-2">Models</span>
			<div class="flex items-center justify-between gap-2 text-sm">
				<span class="text-secondary">Investigations</span>
				<span class="truncate font-mono text-xs" :title="config.models?.investigation ?? ''">
					<bdi>{{ config.models?.investigation ?? "Not reported" }}</bdi>
				</span>
			</div>
			<div class="flex items-center justify-between gap-2 text-sm">
				<span class="text-secondary">Chat</span>
				<span class="truncate font-mono text-xs" :title="config.models?.chat ?? ''">
					<bdi>{{ config.models?.chat ?? "Not reported" }}</bdi>
				</span>
			</div>
		</section>

		<section class="flex flex-col gap-2">
			<span :class="SECTION_LABEL">Features</span>
			<div
				v-for="item of switches"
				:key="item.key"
				class="flex items-center justify-between gap-2 text-sm"
				:data-testid="`talon-config-switch-${item.key}`"
			>
				<span class="text-secondary">{{ item.label }}</span>
				<span class="inline-flex items-center gap-1">
					<Icon :name="item.icon" :size="13" class="text-secondary" />
					<bdi>{{ item.text }}</bdi>
				</span>
			</div>
		</section>

		<section class="flex flex-col gap-2">
			<span :class="SECTION_LABEL">Spend and budgets</span>
			<div
				v-for="item of budgets"
				:key="item.key"
				class="flex items-center justify-between gap-2 text-sm"
				:data-testid="`talon-config-budget-${item.key}`"
			>
				<span class="text-secondary">{{ item.label }}</span>
				<span class="font-mono text-xs">{{ item.value }}</span>
			</div>
			<span class="text-tertiary text-xs">
				Spend is every customer's together; a ceiling applies to each customer without one of its own.
			</span>
		</section>
	</div>
</template>

<script setup lang="ts">
// The configuration panel: what talon-analyst reports about itself. Every value is shown as it
// came (bounded by CoPilot), in <bdi>; amounts are decimal strings, shown as they came.
// `live_customers` arrives already cut to the caller's customers (admins see all).
import type { TalonHealthConfig } from "@/types/talonHealth"
import { NTag } from "naive-ui"
import { computed } from "vue"
import Icon from "@/components/common/Icon.vue"
import { SECTION_LABEL } from "@/components/common/section-label"
import { formatCeiling, formatSwitch, formatUsdText, formatWriteback } from "./health"

const { config, scope } = defineProps<{ config: TalonHealthConfig; scope: "deployment" | "assigned" }>()

const liveCustomers = computed(() => (Array.isArray(config.live_customers) ? config.live_customers : []))

const automationLevel = computed(() => {
	const level = config.automation_max_level
	if (typeof level !== "number") return "Not reported"
	return level === 0 ? "Off" : `Level ${level}`
})

const SWITCHES = [
	{ key: "v2_api", label: "v2 API (chat)" },
	{ key: "action_tools", label: "Action proposals" },
	{ key: "endpoint_actions", label: "Endpoint actions" },
	{ key: "intel", label: "Threat intel" },
	{ key: "workspace_tools", label: "Workspace tools" },
	{ key: "chat_browser", label: "Chat browser" }
] as const

const switches = computed(() =>
	SWITCHES.map(item => {
		const value = config[item.key]
		return {
			...item,
			text: formatSwitch(value),
			icon:
				value === true
					? "carbon:checkmark-outline"
					: value === false
						? "carbon:close-outline"
						: "carbon:information"
		}
	})
)

const budgets = computed(() => {
	const b = config.budgets
	if (!b) return [{ key: "none", label: "Budgets", value: "Not reported" }]
	// Spend is the deployment's, by UTC day and month; the ceilings are the default per customer, so
	// the two aren't set against each other.
	return [
		{ key: "spent-today", label: "Spent today (UTC, all customers)", value: formatUsdText(b.spent_today_usd) },
		{ key: "spent-month", label: "Spent this month (UTC, all customers)", value: formatUsdText(b.spent_month_usd) },
		{ key: "daily", label: "Default daily ceiling per customer", value: formatCeiling(b.daily_usd) },
		{ key: "monthly", label: "Default monthly ceiling per customer", value: formatCeiling(b.monthly_usd) }
	]
})
</script>
