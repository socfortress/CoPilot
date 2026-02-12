import type { Notification } from "./useNotifications"
import _capitalize from "lodash/capitalize"
import { computed, watch } from "vue"
import { useHealthcheckStore } from "@/stores/healthcheck"
import { IndexHealth } from "@/types/indices.d"
import { useNavigation } from "./useNavigation"
import { useNotifications } from "./useNotifications"

export function useHealthchecksNotify() {
	return {
		init: () => {
			const { routeHealthcheck, routeIndex, routeGraylogMetrics } = useNavigation()

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
							routeGraylogMetrics()
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
							routeIndex()
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

			watch(
				alerts,
				(val, old) => {
					if (JSON.stringify(val) !== JSON.stringify(old)) {
						if (val !== null && val.length) {
							const obj: Notification = {
								id: "influxDBAlert",
								category: "alert",
								type: "warning",
								title: "Influx Alert",
								description: `${val.length} Critical ${val.length > 1 ? "issues" : "issue"}`,
								read: false,
								date: new Date(),
								action() {
									routeHealthcheck()
								},
								actionTitle: "See Healthcheck"
							}

							useNotifications().prepend(obj, { autoNotify: true })
						} else {
							useNotifications().deleteOne("influxDBAlert")
						}
					}
				},
				{ deep: true }
			)
		}
	}
}
