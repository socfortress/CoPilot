<template>
	<div class="contents">
		<n-button :loading="loadingInvoke" type="success" secondary :size="size" @click.stop="invoke()">
			<template #icon>
				<Icon :name="InvokeIcon"></Icon>
			</template>
			Invoke
		</n-button>
		<n-button :loading="loadingDelete" :size="size" type="error" secondary @click.stop="handleDelete()">
			<template #icon>
				<Icon :name="DeleteIcon"></Icon>
			</template>
			Delete
		</n-button>
	</div>
</template>

<script setup lang="ts">
import type { Size } from "naive-ui/es/button/src/interface"
import type { MonitoringAlert } from "@/types/monitoringAlerts.d"
import { NButton, useDialog, useMessage } from "naive-ui"
import { computed, ref, watch } from "vue"
import Api from "@/api"
import Icon from "@/components/common/Icon.vue"

const { alert, size } = defineProps<{
	alert: MonitoringAlert
	size?: Size
}>()

const emit = defineEmits<{
	(e: "startInvoking"): void
	(e: "stopInvoking"): void
	(e: "startDeleting"): void
	(e: "stopDeleting"): void
	(e: "startLoading"): void
	(e: "stopLoading"): void
	(e: "invoked"): void
	(e: "deleted"): void
}>()

const DeleteIcon = "ph:trash"
const InvokeIcon = "carbon:play"

const dialog = useDialog()
const message = useMessage()
const loadingInvoke = ref(false)
const loadingDelete = ref(false)
const loading = computed(() => loadingInvoke.value || loadingDelete.value)

watch(loading, val => {
	if (val) {
		emit("startLoading")
	} else {
		emit("stopLoading")
	}
})

watch(loadingInvoke, val => {
	if (val) {
		emit("startInvoking")
	} else {
		emit("stopInvoking")
	}
})

watch(loadingDelete, val => {
	if (val) {
		emit("startDeleting")
	} else {
		emit("stopDeleting")
	}
})

function invoke() {
	loadingInvoke.value = true

	Api.monitoringAlerts
		.invoke(alert.id)
		.then(res => {
			if (res.data.success) {
				emit("invoked")
				message.success(res.data?.message || "Alert invoked successfully")
			} else {
				message.warning(res.data?.message || "An error occurred. Please try again later.")
			}
		})
		.catch(err => {
			message.error(err.response?.data?.message || "An error occurred. Please try again later.")
		})
		.finally(() => {
			loadingInvoke.value = false
		})
}

function handleDelete() {
	dialog.warning({
		title: "Confirm",
		content: "This will delete the alert, are you sure you want to proceed?",
		positiveText: "Yes I'm sure",
		negativeText: "Cancel",
		onPositiveClick: () => {
			deleteAlert()
		},
		onNegativeClick: () => {
			message.info("Delete canceled")
		}
	})
}

function deleteAlert() {
	loadingDelete.value = true

	Api.monitoringAlerts
		.deleteAlert(alert.id)
		.then(res => {
			if (res.data.success) {
				emit("deleted")
				message.success(res.data?.message || "Alert deleted successfully.")
			} else {
				message.warning(res.data?.message || "An error occurred. Please try again later.")
			}
		})
		.catch(err => {
			message.error(err.response?.data?.message || "An error occurred. Please try again later.")
		})
		.finally(() => {
			loadingDelete.value = false
		})
}
</script>
