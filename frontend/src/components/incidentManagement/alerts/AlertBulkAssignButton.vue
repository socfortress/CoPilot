<template>
	<n-popselect
		v-model:value="userSelected"
		v-model:show="usersListVisible"
		:options="usersOptions"
		:disabled="loading"
		size="medium"
		scrollable
		to="body"
	>
		<n-button :size secondary :loading>
			<template #icon>
				<Icon :name="AssigneeIcon" />
			</template>
			Assignee
		</n-button>
	</n-popselect>
</template>

<script setup lang="ts">
import type { ButtonSize } from "naive-ui"
import type { Ref } from "vue"
import type { ApiError } from "@/types/common"
import type { Alert } from "@/types/incidentManagement/alerts"
import { NButton, NPopselect, useMessage } from "naive-ui"
import { computed, inject, ref, watch } from "vue"
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

const AssigneeIcon = "carbon:user-avatar"

const loading = ref(false)
const message = useMessage()
const usersListVisible = ref(false)
const users = inject<Ref<string[]>>("assignable-users", ref([]))
const userSelected = ref<string | null>(null)
const usersOptions = computed(() => users.value.map(user => ({ label: user, value: user })))

function updateAssignee() {
	const assignee = userSelected.value
	if (!assignee) return

	// Alerts already assigned to this user are excluded: the backend keeps them silent
	// (no ALERT_ASSIGNED notification on a no-op), and sending them would inflate the
	// count reported back to the analyst.
	const targets = alerts.filter(alert => alert.assigned_to !== assignee)

	if (!targets.length) {
		message.info(`All selected alerts are already assigned to ${assignee}.`)
		return
	}

	loading.value = true

	Api.incidentManagement.alerts
		.bulkUpdateAlertAssignedUser(
			targets.map(alert => alert.id),
			assignee
		)
		.then(res => {
			if (res.data.success) {
				const updatedIds = new Set(res.data.updated_alert_ids)
				const skippedCount = res.data.not_updated_alert_ids?.length ?? 0

				for (const alert of targets) {
					if (updatedIds.has(alert.id)) {
						emit("updated", { ...alert, assigned_to: assignee })
					}
				}

				if (updatedIds.size && skippedCount) {
					message.warning(`Assigned ${updatedIds.size} alert(s). ${skippedCount} could not be assigned.`)
				} else if (updatedIds.size) {
					message.success(res.data?.message || `Assigned ${updatedIds.size} alert(s).`)
				} else {
					message.warning("The selected alerts could not be assigned.")
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
			userSelected.value = null
		})
}

watch(userSelected, () => {
	if (userSelected.value) {
		updateAssignee()
	}
})
</script>
