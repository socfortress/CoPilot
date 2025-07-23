import type { Notification } from "./useNotifications"
import _capitalize from "lodash/capitalize"
import { computed, watch } from "vue"
import { useHealthcheckStore } from "@/stores/healthcheck"
import { IndexHealth } from "@/types/indices.d"
import { useGoto } from "./useGoto"
import { useNotifications } from "./useNotifications"

export function useHealthchecksNotify() {
	return {
		init: () => {
			const { gotoHealthcheck, gotoIndex, gotoGraylogMetrics } = useGoto()

			const uncommittedJournalEntriesThreshold = useHealthcheckStore().uncommittedJournalEntriesThreshold
			const uncommittedJournalEntries = computed(() => useHealthcheckStore().uncommittedJournalEntries)
			const clusterName = computed(() => useHealthcheckStore().clusterName)
			const clusterStatus = computed(() => useHealthcheckStore().clusterStatus)
			const alerts = computed(() => useHealthcheckStore().alerts)

			useHealthcheckStore().start()

			watch(uncommittedJournalEntries, (val, old) => {
				if (val !== old) {
					const obj: Notification = {
						id: "uncommittedJournalEntries",
						category: "alert",
						type: "error",
						title: "Error check",
						description: "Uncommitted Journal Entries",
						read: false,
						date: new Date(),
						action() {
							gotoGraylogMetrics()
						},
						actionTitle: "See Graylog Metrics"
					}

					if (val !== null && val >= uncommittedJournalEntriesThreshold) {
						obj.type = "warning"
						obj.title = "Uncommitted Journal Entries"
						obj.description = `Value ${val} (over ${uncommittedJournalEntriesThreshold})`
					}

					useNotifications().prepend(obj, { autoNotify: true })
				}
			})

			watch(clusterStatus, (val, old) => {
				if (val !== old) {
					const obj: Notification = {
						id: "clusterHealth",
						category: "alert",
						type: "error",
						title: "Error check",
						description: "Cluster Health",
						read: false,
						date: new Date(),
						action() {
							gotoIndex()
						},
						actionTitle: "See Cluster"
					}

					if (val !== null && val !== IndexHealth.GREEN) {
						obj.type = val === IndexHealth.YELLOW ? "warning" : "error"
						obj.title = "Cluster Health"
						obj.description = `${_capitalize(clusterName.value || "Cluster")} is ${val.toUpperCase()}`
					}

					useNotifications().prepend(obj, { autoNotify: true })
				}
			})

			watch(alerts, (val, old) => {
				if (val?.length !== old?.length) {
					const obj: Notification = {
						id: "influxDBAlert",
						category: "alert",
						type: "error",
						title: "Error check",
						description: "Influx Alert",
						read: false,
						date: new Date(),
						action() {
							gotoHealthcheck()
						},
						actionTitle: "See Healthcheck"
					}

					if (val !== null && val.length) {
						obj.type = "warning"
						obj.title = "Influx Alert"
						obj.description = `${val.length} Critical ${val.length > 1 ? "issues" : "issue"}`
					}

					useNotifications().prepend(obj, { autoNotify: true })
				}
			})
		}
	}
}
