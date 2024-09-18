<template>
	<n-button secondary type="primary" :loading="creating" @click="createCase()">
		<template #icon>
			<Icon :name="DangerIcon" />
		</template>
		Create case
	</n-button>
</template>

<script setup lang="ts">
import type { Alert } from "@/types/incidentManagement/alerts.d"
import Api from "@/api"
import Icon from "@/components/common/Icon.vue"
import { NButton, useMessage } from "naive-ui"
import { ref, toRefs } from "vue"

const props = defineProps<{ alert: Alert }>()
const emit = defineEmits<{
	(e: "updated", value: Alert): void
}>()

const { alert } = toRefs(props)

const DangerIcon = "majesticons:exclamation-line"

const message = useMessage()
const creating = ref(false)

function updateAlert(updatedAlert: Alert) {
	emit("updated", updatedAlert)
}

function createCase() {
	creating.value = true

	Api.incidentManagement
		.createCaseFromAlert(alert.value.id)
		.then(res => {
			if (res.data.success) {
				updateAlert({
					...alert.value,
					linked_cases: [
						{
							id: res.data.case_alert_link.case_id,
							case_name: "",
							case_description: "",
							case_creation_time: new Date(),
							assigned_to: null,
							case_status: null
						}
					]
				})
				message.success(res.data?.message || "Case created successfully")
			} else {
				message.warning(res.data?.message || "An error occurred. Please try again later.")
			}
		})
		.catch(err => {
			message.error(err.response?.data?.message || "An error occurred. Please try again later.")
		})
		.finally(() => {
			creating.value = false
		})
}
</script>
