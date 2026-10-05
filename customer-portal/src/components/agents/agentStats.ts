import type { StatusStripCell } from "@/components/common/StatusStrip.vue"
import type { StatusSegment } from "@/components/overview/shared/status"
import type { AgentsStats } from "@/types/agents"

/**
 * The agents' cells in the status strip: active and offline (the Overview's online /
 * offline colours) and critical — a flag on an asset, counted across both, so it carries
 * an icon rather than a dot and is no share of the bar.
 */
export function agentStatusCells(stats: AgentsStats): StatusStripCell[] {
	return [
		{ key: "active", label: "active", value: stats.active, color: "success" },
		{ key: "offline", label: "offline", value: stats.offline, color: "error" },
		{ key: "critical", label: "critical", value: stats.critical, color: "warning", icon: "carbon:warning-alt" }
	]
}

/**
 * What the bar under the total shows: active and offline, plus whatever is neither
 * (Wazuh also reports agents as pending, for one) so the bar always adds up to the total.
 */
export function agentStatusSplit(stats: AgentsStats): StatusSegment[] {
	const other = Math.max(0, stats.total - stats.active - stats.offline)
	return [
		{ key: "active", label: "active", value: stats.active, color: "success" },
		{ key: "offline", label: "offline", value: stats.offline, color: "error" },
		...(other ? [{ key: "other", label: "other", value: other, color: "neutral" as const }] : [])
	]
}
