import _toNumber from "lodash/toNumber"
import { InfluxDBAlertLevel, type InfluxDBAlert } from "@/types/healthchecks.d"
import Api from "@/api"
import { defineStore, acceptHMRUpdate } from "pinia"
import { IndexHealth } from "@/types/indices.d"

export const usHealthcheckStore = defineStore("healthcheck", {
	state: () => ({
		uncommittedJournalEntriesThreshold: _toNumber(
			import.meta.env.VITE_UNCOMMITTED_JOURNAL_ENTRIES_THRESHOLD
		) as number,
		healthchecksInterval: (_toNumber(import.meta.env.VITE_HEALTHCHECKS_INTERVAL) * 1000) as number,
		getDataTimer: null as NodeJS.Timeout | null,
		uncommittedJournalEntries: 0 as number | null,
		clusterName: "" as string | null,
		clusterStatus: IndexHealth.GREEN as IndexHealth | null,
		alerts: [] as InfluxDBAlert[] | null
	}),
	actions: {
		getGraylogCheck() {
			Api.graylog
				.getMetrics()
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
			Api.indices
				.getClusterHealth()
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
				.getHealthchecks()
				.then(res => {
					if (res.data.success) {
						this.alerts = res.data.alerts.filter(o => o.level === InfluxDBAlertLevel.Crit)
					} else {
						this.alerts = null
					}
				})
				.catch(() => {
					this.alerts = null
				})
		},

		getData() {
			if (this.uncommittedJournalEntriesThreshold) {
				this.getGraylogCheck()
			}
			this.getClusterHealth()
			this.getHealthchecks()
		},

		stop() {
			if (this.getDataTimer !== null) {
				clearInterval(this.getDataTimer)
				this.getDataTimer = null
			}
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
	import.meta.hot.accept(acceptHMRUpdate(usHealthcheckStore, import.meta.hot))
}
