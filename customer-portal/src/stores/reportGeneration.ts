import type { Notification } from "@/composables/common/useNotifications"
import type { IncidentCustomerReportStatus } from "@/types/reports"
import { acceptHMRUpdate, defineStore } from "pinia"
import Api from "@/api"
import { useNotifications } from "@/composables/common/useNotifications"

/**
 * Tracks report generations until the backend reports them done, wherever the user
 * happens to be in the portal.
 *
 * Why polling and not a socket: the backend exposes no WebSocket or SSE channel for
 * reports — generation is a FastAPI background task whose only observable state is
 * the report's `status`. Swap this store for a subscription the day such a channel
 * exists; nothing outside it needs to change.
 *
 * Each poll asks `GET /incidents/customer_reports/status` about the pending reports only
 * (#1263), never the whole list, and one request at a time. It asks often at first, when
 * most reports finish, then less and less (`pollDelay`). The poller lives here rather than
 * in the Reports page so it survives navigation, and stops as soon as nothing is pending:
 * an idle portal makes no requests at all.
 */

/** After this long a report stops being watched; the Reports page still shows its real state. */
export const POLL_TIMEOUT_MS = 15 * 60 * 1000
/** The most ids one status request may carry (the backend's own limit). */
export const STATUS_BATCH = 50

/** How long to wait before asking again, given how long the newest report has been running. */
export function pollDelay(elapsedMs: number): number {
	if (elapsedMs < 60_000) return 3_000
	if (elapsedMs < 5 * 60_000) return 10_000
	return 30_000
}

export interface PendingReport {
	id: number
	name: string
	/** Epoch ms; used for the give-up deadline and kept serialisable for persistence. */
	startedAt: number
}

/** Where the Reports page opens to download a report: a route, so the bell can keep it. */
export function downloadRoute(reportId: number): NonNullable<Notification["actionRoute"]> {
	return { name: "ReportsList", query: { download: String(reportId) } }
}

function notify(report: PendingReport, status: IncidentCustomerReportStatus["status"] | "timeout", error?: string | null) {
	const base = {
		id: `report-${report.id}`,
		category: "report" as const,
		read: false,
		date: new Date()
	}

	const item: Notification =
		status === "completed"
			? {
					...base,
					type: "success",
					title: "Report ready",
					description: `"${report.name}" has been generated and is ready to download.`,
					// Straight to the file, from the toast or later from the bell.
					actionRoute: downloadRoute(report.id),
					actionTitle: "Download"
				}
			: status === "failed"
				? {
						...base,
						type: "error",
						title: "Report failed",
						description: error?.trim() || `"${report.name}" could not be generated.`,
						actionRoute: { name: "ReportsList" },
						actionTitle: "View reports"
					}
				: {
						...base,
						type: "warning",
						title: "Report still running",
						description: `"${report.name}" is taking longer than expected. Check the Reports page for its status.`,
						actionRoute: { name: "ReportsList" },
						actionTitle: "View reports"
					}

	useNotifications().prepend(item, { sendNotify: true })
}

/**
 * The timer and the in-flight flag are module state on purpose: they are not
 * serialisable and have no business being reactive or persisted.
 */
let pollTimer: ReturnType<typeof setTimeout> | null = null
let inFlight = false

export const useReportGenerationStore = defineStore("report-generation", {
	state: () => ({
		pending: [] as PendingReport[],
		/** Bumped whenever a report leaves "processing", so open views can refresh. */
		lastResolvedAt: 0
	}),
	getters: {
		isGenerating: state => state.pending.length > 0,
		pendingCount: state => state.pending.length,
		isPending: state => (reportId: number) => state.pending.some(r => r.id === reportId)
	},
	actions: {
		/** Watch a freshly queued report. Safe to call for several reports at once. */
		track(report: { id: number; name: string }) {
			if (this.pending.some(r => r.id === report.id)) return

			this.pending.push({ id: report.id, name: report.name, startedAt: Date.now() })
			// A new report is the newest: ask again soon, whatever the current pace.
			schedule()
		},

		/** Resume watching after a page reload (the pending list is persisted). */
		resume() {
			if (this.pending.length) {
				schedule()
			}
		},

		stop() {
			stopPolling()
		},

		/** Drop everything — called on logout, where the session's reports stop being ours. */
		reset() {
			stopPolling()
			this.pending = []
			this.lastResolvedAt = 0
		},

		/** One poll: ask where the pending reports stand, and resolve those that are done. */
		async poll() {
			if (inFlight) return
			if (!this.pending.length) {
				stopPolling()
				return
			}

			inFlight = true
			try {
				const asked = this.pending.slice(0, STATUS_BATCH).map(r => r.id)
				let statuses: IncidentCustomerReportStatus[]
				let missing: number[]
				try {
					const response = await Api.reports.getReportStatuses(asked)
					if (!response.data.success) return
					statuses = response.data.reports
					missing = response.data.missing
				} catch {
					// Transient failure (the backend is busy generating): keep waiting, the
					// deadline below is what eventually gives up.
					return
				}

				const byId = new Map(statuses.map(status => [status.id, status]))
				const gone = new Set(missing)
				const now = Date.now()
				let resolved = false

				this.pending = this.pending.filter(pending => {
					// Beyond this batch: asked about on the next poll.
					if (!asked.includes(pending.id)) return true

					// Deleted while generating, or no longer ours to see: nothing to tell.
					if (gone.has(pending.id)) {
						resolved = true
						return false
					}

					const status = byId.get(pending.id)
					if (status && status.status !== "processing") {
						notify(pending, status.status, status.error_message)
						resolved = true
						return false
					}

					if (now - pending.startedAt > POLL_TIMEOUT_MS) {
						notify(pending, "timeout")
						resolved = true
						return false
					}

					return true
				})

				if (resolved) {
					this.lastResolvedAt = now
				}
			} finally {
				inFlight = false
				schedule()
			}
		}
	},
	persist: {
		storage: sessionStorage,
		pick: ["pending"]
	}
})

/** Ask again after the delay the newest pending report calls for; nothing pending, no timer. */
function schedule() {
	const store = useReportGenerationStore()
	stopPolling()
	if (!store.pending.length || inFlight) return

	const newest = Math.max(...store.pending.map(r => r.startedAt))
	pollTimer = setTimeout(() => {
		pollTimer = null
		store.poll()
	}, pollDelay(Date.now() - newest))
}

function stopPolling() {
	if (pollTimer === null) return

	clearTimeout(pollTimer)
	pollTimer = null
}

if (import.meta.hot) {
	import.meta.hot.accept(acceptHMRUpdate(useReportGenerationStore, import.meta.hot))
}
