import { computed, watch } from "vue"
import { usHealthcheckStore } from "@/stores/healthcheck"
import { useNotifications, type Notification } from "./useNotifications"
import { IndexHealth } from "@/types/indices.d"
import { useRouter } from "vue-router"
import _capitalize from "lodash/capitalize"

export function useHealthchecksNotify() {
	return {
		init: () => {
			const router = useRouter()

			const uncommittedJournalEntriesThreshold = usHealthcheckStore().uncommittedJournalEntriesThreshold
			const uncommittedJournalEntries = computed(() => usHealthcheckStore().uncommittedJournalEntries)
			const clusterName = computed(() => usHealthcheckStore().clusterName)
			const clusterStatus = computed(() => usHealthcheckStore().clusterStatus)
			const alerts = computed(() => usHealthcheckStore().alerts)

			usHealthcheckStore().start()

			watch(uncommittedJournalEntries, (val, old) => {
				if (val != old) {
					const obj: Notification = {
						id: "uncommittedJournalEntries",
						category: "alert",
						type: "error",
						title: "Error check",
						description: "Uncommitted Journal Entries",
						read: false,
						date: new Date(),
						action() {
							router.push({ name: "Graylog-Metrics" })
						},
						actionTitle: "See Graylog Metrics"
					}

					if (val === null) {
						useNotifications().prepend(obj)
					} else if (val >= uncommittedJournalEntriesThreshold) {
						obj.type = "warning"
						obj.title = "Uncommitted Journal Entries"
						obj.description = `Value ${val} (over ${uncommittedJournalEntriesThreshold})`
						useNotifications().prepend(obj)
					}
				}
			})

			watch(clusterStatus, (val, old) => {
				if (val != old) {
					const obj: Notification = {
						id: "clusterHealth",
						category: "alert",
						type: "error",
						title: "Error check",
						description: "Cluster Health",
						read: false,
						date: new Date(),
						action() {
							router.push({ name: "Indices" })
						},
						actionTitle: "See Cluster"
					}

					if (val === null) {
						useNotifications().prepend(obj)
					} else if (val !== IndexHealth.GREEN) {
						obj.type = val === IndexHealth.YELLOW ? "warning" : "error"
						obj.title = "Cluster Health"
						obj.description = `${_capitalize(clusterName.value || "Cluster")} is ${val.toUpperCase()}`
						useNotifications().prepend(obj)
					}
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
						},
						actionTitle: "See Healthcheck"
					}

					if (val === null) {
						useNotifications().prepend(obj)
					} else if (val.length) {
						obj.type = "warning"
						obj.title = "Influx Alert"
						obj.description = `${val.length} Critical ${val.length > 1 ? "issues" : "issue"}`
						useNotifications().prepend(obj)
					}
				}
			})
		}
	}
}
