<template>
	<n-popselect
		v-model:value="statusSelected"
		v-model:show="listVisible"
		:options="statusOptions"
		:disabled="loading"
		size="medium"
		scrollable
		to="body"
	>
		<n-button :size secondary :loading>
			<template #icon>
				<Icon :name="StatusIcon" />
			</template>
			Status
		</n-button>
	</n-popselect>
</template>

<script setup lang="ts">
import type { ButtonSize } from "naive-ui"
import type { ApiError } from "@/types/common"
import type { Alert, AlertStatus } from "@/types/incidentManagement/alerts"
import { NButton, NPopselect, useMessage } from "naive-ui"
import { ref, watch } from "vue"
import Api from "@/api"
import Icon from "@/components/common/Icon.vue"
import { getApiErrorMessage } from "@/utils"

const { alerts, size } = defineProps<{
	alerts: Alert[]
	size?: ButtonSize
}>()

const emit = defineEmits<{
	(e: "updated", value: Alert): void
	(e: "done"): void
}>()

const StatusIcon = "carbon:progress-bar-round"

const loading = ref(false)
const message = useMessage()
const listVisible = ref(false)
const statusSelected = ref<AlertStatus | null>(null)
const statusOptions = ref<{ label: string; value: AlertStatus }[]>([
	{ label: "Open", value: "OPEN" },
	{ label: "In progress", value: "IN_PROGRESS" },
	{ label: "Closed", value: "CLOSED" }
])

function updateStatus() {
	const status = statusSelected.value
	if (!status) return

	// Alerts already at the requested status are left out of the request rather than
	// rewritten — the backend would accept them, but sending them makes the "updated N"
	// count meaningless to the analyst who just pressed the button.
	const targets = alerts.filter(alert => alert.status !== status)

	if (!targets.length) {
		message.info(`All selected alerts are already ${status.replace("_", " ").toLowerCase()}.`)
		return
	}

	loading.value = true

	Api.incidentManagement.alerts
		.bulkUpdateAlertStatus(
			targets.map(alert => alert.id),
			status
		)
		.then(res => {
			if (res.data.success) {
				const updatedIds = new Set(res.data.updated_alert_ids)
				const skippedCount = res.data.not_updated_alert_ids?.length ?? 0

				// Patch locally instead of refetching: the new value is known, and a refetch
				// would drop the analyst's scroll position mid-triage.
				for (const alert of targets) {
					if (updatedIds.has(alert.id)) {
						emit("updated", { ...alert, status })
					}
				}

				if (updatedIds.size && skippedCount) {
					message.warning(`Updated ${updatedIds.size} alert(s). ${skippedCount} could not be updated.`)
				} else if (updatedIds.size) {
					message.success(res.data?.message || `Updated ${updatedIds.size} alert(s).`)
				} else {
					message.warning("The selected alerts could not be updated.")
				}

				emit("done")
			} else {
				message.warning(res.data?.message || "An error occurred. Please try again later.")
			}
		})
		.catch((err: ApiError) => {
			message.error(getApiErrorMessage(err))
		})
		.finally(() => {
			loading.value = false
			statusSelected.value = null
		})
}

watch(statusSelected, () => {
	if (statusSelected.value) {
		updateStatus()
	}
})
</script>
