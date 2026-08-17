import type { InfluxDBAlert } from "@/types/healthchecks"
import _toNumber from "lodash/toNumber"
import { acceptHMRUpdate, defineStore } from "pinia"
import Api from "@/api"
import { InfluxDBAlertSeverity } from "@/types/healthchecks"
import { IndexHealth } from "@/types/indices"
import { useAuthStore } from "./auth"

/**
 * Owns the cancellation of this store's polling (#1072).
 *
 * These three checks feed the sidebar healthcheck indicator and the toolbar
 * notification bell, which live *across* navigation — they are not page-scoped.
 * Passing an explicit signal keeps them out of the router's navigation scope
 * (a caller-supplied signal always wins), so changing page no longer kills the
 * poll and blanks the indicator until the next interval tick.
 *
 * Kept outside `state` deliberately: an AbortController is not serialisable and
 * has no business being reactive or persisted.
 */
let pollAbortController: AbortController | null = null

function pollSignal(): AbortSignal {
	if (!pollAbortController) {
		pollAbortController = new AbortController()
	}
	return pollAbortController.signal
}

export const useHealthcheckStore = defineStore("healthcheck", {
	state: () => ({
		uncommittedJournalEntriesThreshold: _toNumber(import.meta.env.VITE_UNCOMMITTED_JOURNAL_ENTRIES_THRESHOLD),
		healthchecksInterval: _toNumber(import.meta.env.VITE_HEALTHCHECKS_INTERVAL) * 1000,
		getDataTimer: null as NodeJS.Timeout | null,
		uncommittedJournalEntries: 0 as number | null,
		clusterName: "" as string | null,
		clusterStatus: IndexHealth.GREEN as IndexHealth | null,
		alerts: null as InfluxDBAlert[] | null
	}),
	actions: {
		getGraylogCheck() {
			Api.graylog
				.getMetrics(pollSignal())
				.then(res => {
					if (res.data.success) {
						this.uncommittedJournalEntries = res.data.uncommitted_journal_entries || 0
					} else {
						this.uncommittedJournalEntries = null
					}
				})
				.catch(() => {
					this.uncommittedJournalEntries = null
				})
		},
		getClusterHealth() {
			Api.wazuh.indices
				.getClusterHealth(pollSignal())
				.then(res => {
					if (res.data.success) {
						this.clusterName = res.data.cluster_health.cluster_name
						this.clusterStatus = res.data.cluster_health.status
					} else {
						this.clusterName = null
						this.clusterStatus = null
					}
				})
				.catch(() => {
					this.clusterName = null
					this.clusterStatus = null
				})
		},
		getHealthchecks() {
			Api.healthchecks
				.getHealthchecks(
					{
						days: 1,
						status: "active",
						exclude_ok: true
					},
					pollSignal()
				)
				.then(res => {
					if (res.data.success) {
						// Filter to only show critical alerts
						this.alerts = res.data.alerts.filter(o => o.severity === InfluxDBAlertSeverity.Critical)
					} else {
						this.alerts = null
					}
				})
				.catch(() => {
					this.alerts = null
				})
		},

		getData() {
			const authStore = useAuthStore()

			if (authStore.isLogged) {
				if (this.uncommittedJournalEntriesThreshold) {
					this.getGraylogCheck()
					// this.getClusterHealth()
					this.getHealthchecks()
				}
			}
		},

		stop() {
			if (this.getDataTimer !== null) {
				clearInterval(this.getDataTimer)
				this.getDataTimer = null
			}
			// Drop any poll still in flight, and arm a fresh controller for the next
			// start() — an aborted signal stays aborted and would kill every retry.
			pollAbortController?.abort()
			pollAbortController = null
		},

		start() {
			this.getData()
			if (this.healthchecksInterval) {
				this.getDataTimer = setInterval(this.getData, this.healthchecksInterval)
			}
		}
	}
})

if (import.meta.hot) {
	import.meta.hot.accept(acceptHMRUpdate(useHealthcheckStore, import.meta.hot))
}
