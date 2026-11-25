import type { DialogApi, MessageApi } from "naive-ui"
import type { ApiError } from "@/types/common"
import type { StatsCustomer, StatsStatus, StatsWeekState } from "@/types/sysmon-config"
import Api from "@/api"
import { getApiErrorMessage } from "@/utils"

export type StatsTone = "success" | "warning" | "info"

/** One line on the Sysmon Config page about the weekly noise statistics, like the default sync's line. */
export interface StatsLine {
	text: string
	detail: string | null
	tone: StatsTone
	icon: string
	iconClass: string
	canSend: boolean
	/** Reports are paused after a refusal: Resume lifts the pause. */
	latched: boolean
}

const ICONS: Record<StatsTone, string> = {
	success: "carbon:checkmark-outline",
	warning: "carbon:warning-alt",
	info: "carbon:information"
}
const ICON_CLASSES: Record<StatsTone, string> = { success: "text-success", warning: "text-warning", info: "text-secondary" }

const REFUSED = new Set(["refused", "local_refused", "refused_bad_request", "refused_content_type", "too_large", "waf_refused"])

export function statsLine(status: StatsStatus | null): StatsLine | null {
	if (!status) return null
	const line = (text: string, tone: StatsTone, detail: string | null, extra: Partial<StatsLine> = {}): StatsLine => ({
		text,
		detail: status.read_error || detail,
		tone,
		icon: ICONS[tone],
		iconClass: ICON_CLASSES[tone],
		canSend: true,
		latched: false,
		...extra
	})

	if (status.mode === "off") {
		const setting = status.mode_setting ? ` (SYSMON_STATS_SHARING=${status.mode_setting})` : " (SYSMON_STATS_SHARING=off)"
		return line(`Noise statistics: off${setting}`, "info", null, { canSend: false })
	}
	if (status.latch) {
		return line(
			`Paused: SOCFortress refused a report (${status.latch.reason}). Update CoPilot, or Resume`,
			"warning",
			null,
			{ latched: true }
		)
	}
	if (status.service.accepting === false) {
		return line("SOCFortress is not accepting noise reports yet", "info", status.last_tick?.message ?? null)
	}
	const week = status.target_week
	const sharing = status.customers.filter(c => c.sharing)
	const sent = sharing.filter(c => c.target_week_state?.outcome === "sent").length
	const refused = sharing.some(c => c.target_week_state && REFUSED.has(c.target_week_state.outcome))
	return line(
		`Noise statistics ${week}: sent for ${sent} of ${sharing.length} customer${sharing.length === 1 ? "" : "s"}`,
		refused ? "warning" : sent ? "success" : "info",
		status.last_tick?.message ?? null
	)
}

/** "W47 sent 24 Nov 06:12 · 41 patterns, 41 accepted", or the outcome. */
export function weekStateText(week: string | null, state: StatsWeekState | null, formatDate: (iso: string) => string): string {
	if (!state) return "Not sent yet"
	const shortWeek = week ? week.replace(/^\d{4}-/, "") : ""
	if (state.outcome === "sent") {
		const when = state.sent_at ? ` ${formatDate(state.sent_at)}` : ""
		const accepted = state.accepted != null ? `, ${state.accepted} accepted` : ""
		return `${shortWeek} sent${when} · ${state.patterns ?? 0} patterns${accepted}`.trim()
	}
	return `${shortWeek} ${state.outcome.replace(/_/g, " ")}${state.status === "pending" ? " (retried)" : ""}`.trim()
}

/**
 * Turn a customer's noise statistics off (after a confirmation: the reports already sent are withdrawn) or on. Resolves
 * with the customer as the backend now has it, or null when cancelled or failed.
 */
export function toggleSharing(
	dialog: DialogApi,
	message: MessageApi,
	customer: StatsCustomer,
	sharing: boolean
): Promise<StatsCustomer | null> {
	const label = customer.customer_name ? `${customer.customer_code} (${customer.customer_name})` : customer.customer_code
	const send = () =>
		Api.sysmonConfig
			.setStatsSharing(customer.customer_code, { sharing })
			.then(res => {
				if (!res.data.success) {
					message.error(res.data.message || "An error occurred. Please try again later.")
					return null
				}
				if (!sharing) {
					const withdraw = res.data.withdraw
					if (withdraw?.outcome === "withdrawn") {
						message.success(
							`Noise statistics off for ${label}. SOCFortress deleted ${withdraw.reports_deleted ?? 0} report(s) already sent.`,
							{ duration: 10000, closable: true }
						)
					} else {
						message.warning(
							`Noise statistics off for ${label}. The deletion of the reports already sent is queued: ${withdraw?.message ?? ""}`,
							{ duration: 10000, closable: true }
						)
					}
				} else {
					message.info(
						"Sharing resumes with the next weekly report (not sooner than 3 minutes after the withdraw).",
						{ duration: 10000, closable: true }
					)
				}
				return res.data.customer
			})
			.catch(err => {
				message.error(getApiErrorMessage(err as ApiError) || "An error occurred. Please try again later.")
				return null
			})

	if (sharing) return send()
	return new Promise(resolve => {
		dialog.warning({
			title: "Stop sharing noise statistics",
			// Plain text, never HTML: the customer code and name are data.
			content: `Stop sharing noise statistics for ${label}? CoPilot stops its weekly report and asks SOCFortress to delete the reports already sent.`,
			positiveText: "Stop sharing",
			negativeText: "Cancel",
			onPositiveClick: () => {
				send().then(resolve)
			},
			onNegativeClick: () => resolve(null),
			onClose: () => resolve(null)
		})
	})
}
