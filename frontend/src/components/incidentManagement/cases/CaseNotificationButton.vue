<template>
	<n-tooltip trigger="hover">
		<template #trigger>
			<n-button :size :loading="invoking" secondary @click="invoke()">
				<template #icon>
					<Icon :name="NotificationIcon" />
				</template>
				Invoke Customer Notification
			</n-button>
		</template>
		<div>
			Invoked
			<code>{{ notificationInvokedNumber }}</code>
			{{ notificationInvokedNumber === 1 ? "time" : "times" }}
		</div>
	</n-tooltip>
</template>

<script setup lang="ts">
import type { Size } from "naive-ui/es/button/src/interface"
import Api from "@/api"
import Icon from "@/components/common/Icon.vue"
import { NButton, NTooltip, useMessage } from "naive-ui"
import { ref } from "vue"

const { size, caseId, notificationInvokedNumber } = defineProps<{
	size?: Size
	caseId: number
	notificationInvokedNumber: number
}>()

const emit = defineEmits<{
	(e: "invoked"): void
}>()

const NotificationIcon = "ph:bell"
const invoking = ref(false)
const message = useMessage()

function invoke() {
	invoking.value = true

	Api.incidentManagement.cases
		.createCaseNotification(caseId)
		.then(res => {
			if (res.data) {
				emit("invoked")
				message.success(res.data.message || "Case notification created successfully.")
			} else {
				message.warning("An error occurred. Please try again later.")
			}
		})
		.catch(err => {
			message.error(err.response?.data?.message || "An error occurred. Please try again later.")
		})
		.finally(() => {
			invoking.value = false
		})
}
</script>
