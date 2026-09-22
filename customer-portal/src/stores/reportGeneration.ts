import type { Notification } from "@/composables/common/useNotifications"
import type { IncidentCustomerReport } from "@/types/reports"
import { acceptHMRUpdate, defineStore } from "pinia"
import Api from "@/api"
import { useNotifications } from "@/composables/common/useNotifications"

/**
 * Tracks report generations until the backend reports them done, wherever the user
 * happens to be in the portal.
 *
 * Why polling and not a socket: the backend exposes no WebSocket or SSE channel for
 * reports — generation is a FastAPI background task whose only observable state is
 * the `status` column returned by `GET /incidents/customer_reports`. Swap this store
 * for a subscription the day such a channel exists; nothing outside it needs to change.
 *
 * The poller lives here rather than in the Reports page so it survives navigation: it
 * starts when the first report is queued and stops as soon as nothing is pending, so
 * an idle portal makes no requests at all. Several generations can be in flight at
 * once — each tick is a single list call that resolves all of them.
 */

const POLL_INTERVAL_MS = 5000
/** After this long a report stops being watched; the Reports page still shows its real state. */
const POLL_TIMEOUT_MS = 15 * 60 * 1000

export interface PendingReport {
	id: number
	name: string
	/** Epoch ms; used for the give-up deadline and kept serialisable for persistence. */
	startedAt: number
}

function notify(report: PendingReport, status: IncidentCustomerReport["status"] | "timeout", error?: string | null) {
	const base = {
		id: `report-${report.id}`,
		category: "report" as const,
		read: false,
		date: new Date(),
		// Clicking the toast button — or the item in the bell — opens the Reports page.
		actionRoute: { name: "ReportsList" },
		actionTitle: "View reports"
	}

	const item: Notification =
		status === "completed"
			? {
					...base,
					type: "success",
					title: "Report ready",
					description: `"${report.name}" has been generated and is ready to download.`
				}
			: status === "failed"
				? {
						...base,
						type: "error",
						title: "Report failed",
						description: error?.trim() || `"${report.name}" could not be generated.`
					}
				: {
						...base,
						type: "warning",
						title: "Report still running",
						description: `"${report.name}" is taking longer than expected. Check the Reports page for its status.`
					}

	useNotifications().prepend(item, { sendNotify: true })
}

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
			startPolling()
		},

		/** Resume watching after a page reload (the pending list is persisted). */
		resume() {
			if (this.pending.length) {
				startPolling()
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

		/** One poll cycle: read the list once and resolve every pending report against it. */
		async poll() {
			if (!this.pending.length) {
				stopPolling()
				return
			}

			let reports: IncidentCustomerReport[]
			try {
				const response = await Api.reports.listReports()
				if (!response.data.success) return
				reports = response.data.reports
			} catch {
				// Transient failure (the backend is busy generating): keep waiting, the
				// deadline below is what eventually gives up.
				return
			}

			const now = Date.now()
			const stillPending: PendingReport[] = []
			let resolved = false

			for (const pending of this.pending) {
				const report = reports.find(r => r.id === pending.id)

				// A report that vanished from the list (deleted while generating) is simply
				// dropped: there is nothing left to notify about.
				if (!report) {
					resolved = true
					continue
				}

				if (report.status !== "processing") {
					notify(pending, report.status, report.error_message)
					resolved = true
					continue
				}

				if (now - pending.startedAt > POLL_TIMEOUT_MS) {
					notify(pending, "timeout")
					resolved = true
					continue
				}

				stillPending.push(pending)
			}

			this.pending = stillPending
			if (resolved) {
				this.lastResolvedAt = now
			}
			if (!stillPending.length) {
				stopPolling()
			}
		}
	},
	persist: {
		storage: sessionStorage,
		pick: ["pending"]
	}
})

/**
 * The timer is module state on purpose: it is not serialisable and has no business
 * being reactive or persisted.
 */
let pollTimer: ReturnType<typeof setInterval> | null = null

function startPolling() {
	if (pollTimer !== null) return

	const store = useReportGenerationStore()
	pollTimer = setInterval(() => {
		store.poll()
	}, POLL_INTERVAL_MS)
}

function stopPolling() {
	if (pollTimer === null) return

	clearInterval(pollTimer)
	pollTimer = null
}

if (import.meta.hot) {
	import.meta.hot.accept(acceptHMRUpdate(useReportGenerationStore, import.meta.hot))
}
