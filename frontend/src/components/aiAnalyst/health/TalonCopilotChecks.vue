<template>
	<div class="flex flex-col gap-3" data-testid="talon-copilot-checks">
		<div class="grid grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-4">
			<div
				v-for="check of checks"
				:key="check.id"
				class="border-default flex flex-col gap-1 rounded-lg border p-3"
				:data-testid="`talon-check-${check.id}`"
				:data-tone="check.tone"
			>
				<span :class="SECTION_LABEL">{{ check.label }}</span>
				<span class="inline-flex items-center gap-1.5 text-sm font-semibold" :style="{ color: TONE_COLOR[check.tone] }">
					<Icon :name="check.icon" :size="15" />
					<span>{{ check.value }}</span>
				</span>
				<span
					v-if="check.detail"
					class="text-tertiary text-xs break-words"
					:title="check.detail"
					:data-testid="`talon-check-${check.id}-detail`"
				>
					<bdi>{{ check.detail }}</bdi>
				</span>
			</div>
		</div>
		<dl class="text-secondary flex flex-wrap gap-x-6 gap-y-1 text-xs" data-testid="talon-copilot-facts">
			<div v-for="fact of facts" :key="fact.label" class="flex gap-1.5">
				<dt>{{ fact.label }}</dt>
				<dd class="text-default font-medium"><bdi>{{ fact.value }}</bdi></dd>
			</div>
		</dl>
		<p v-if="copilot.scope === 'assigned'" class="text-tertiary text-xs">
			Jobs, reports and customer counts cover only the customers assigned to you.
		</p>
	</div>
</template>

<script setup lang="ts">
// "From CoPilot": what CoPilot's backend measured itself, so it shows even when Talon is down.
// Each check is an icon, a word and its tone, never colour alone.
import type { Tone } from "@/components/socManagement/utils"
import type { TalonCopilotView, TalonJobSummary } from "@/types/talonHealth"
import { computed } from "vue"
import Icon from "@/components/common/Icon.vue"
import { SECTION_LABEL } from "@/components/common/section-label"
import { TONE_COLOR } from "@/components/socManagement/utils"
import { formatLatency, formatTime } from "./health"

const { copilot } = defineProps<{ copilot: TalonCopilotView }>()

interface Check {
	id: string
	label: string
	value: string
	detail: string | null
	tone: Tone
	icon: string
}

const GOOD = "carbon:checkmark-filled"
const BAD = "carbon:error-filled"
const WARN = "carbon:warning-alt-filled"
const UNKNOWN = "carbon:help"

const checks = computed((): Check[] => {
	const { connector, reachable, auth } = copilot
	const connectorCheck: Check = !connector?.exists
		? { id: "connector", label: "Connector", value: "Missing", detail: null, tone: "bad", icon: BAD }
		: !connector.configured
			? { id: "connector", label: "Connector", value: "Not configured", detail: "Set the Talon connector's URL and API key", tone: "bad", icon: BAD }
			: connector.verified
				? { id: "connector", label: "Connector", value: "Configured and verified", detail: connector.url, tone: "good", icon: GOOD }
				: { id: "connector", label: "Connector", value: "Configured, not verified", detail: connector.url, tone: "warn", icon: WARN }

	const reachableCheck: Check =
		reachable?.ok === true
			? { id: "reachable", label: "Talon reachable", value: `Yes, ${formatLatency(reachable.latency_ms)}`, detail: null, tone: "good", icon: GOOD }
			: reachable?.ok === false
				? { id: "reachable", label: "Talon reachable", value: "No", detail: reachable.error, tone: "bad", icon: BAD }
				: { id: "reachable", label: "Talon reachable", value: "Not checked", detail: reachable?.error ?? null, tone: "neutral", icon: UNKNOWN }

	const authCheck: Check =
		auth?.ok === true
			? { id: "auth", label: "API key", value: "Accepted", detail: null, tone: "good", icon: GOOD }
			: auth?.ok === false
				? { id: "auth", label: "API key", value: "Refused", detail: auth.error, tone: "bad", icon: BAD }
				: { id: "auth", label: "API key", value: "Not checked", detail: auth?.error ?? null, tone: "neutral", icon: UNKNOWN }

	const v2Check: Check = copilot.v2_enabled
		? { id: "v2", label: "Talon v2 setting", value: "On", detail: "Threaded chat, approvals and usage", tone: "good", icon: GOOD }
		: { id: "v2", label: "Talon v2 setting", value: "Off", detail: "v1 chat; the dashboard works either way", tone: "neutral", icon: "carbon:subtract-alt" }

	return [connectorCheck, reachableCheck, authCheck, v2Check]
})

function when(summary: TalonJobSummary | null, withStatus: boolean) {
	if (!summary) return "none"
	const status = withStatus && summary.status ? `, ${summary.status}` : ""
	return `${formatTime(summary.at)} (${summary.customer_code}${status})`
}

const facts = computed(() => [
	{ label: "Last alert sent", value: when(copilot.last_sent, true) },
	{ label: "Last job", value: when(copilot.last_job, true) },
	{ label: "Last report", value: when(copilot.last_report, false) },
	{ label: "Jobs failed in 24 h", value: String(copilot.jobs_failed_24h ?? 0) },
	{ label: "Customers with the AI trigger on", value: String(copilot.ai_trigger_customers ?? 0) }
])
</script>
