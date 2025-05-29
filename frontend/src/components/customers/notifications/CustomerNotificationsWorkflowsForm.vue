<template>
	<div class="customer-notifications-workflows-form flex grow flex-col justify-between">
		<div class="form-box">
			<n-spin v-model:show="loading">
				<n-form ref="formRef" :label-width="80" :model="form" :rules="rules">
					<n-form-item label="Enabled" path="enabled">
						<n-switch v-model:value="form.enabled" />
					</n-form-item>
					<n-form-item label="Shuffle Workflow Id" path="shuffle_workflow_id">
						<n-input
							v-model:value.trim="form.shuffle_workflow_id"
							placeholder="Input the Shuffle Workflow Id..."
							clearable
						/>
					</n-form-item>
				</n-form>
			</n-spin>
		</div>
		<div class="buttons-box flex justify-between gap-3">
			<div class="flex gap-3">
				<slot name="additionalActions" :loading></slot>
			</div>
			<div class="flex gap-3">
				<n-button secondary :disabled="loading" @click="reset()">Reset</n-button>
				<n-button type="primary" :disabled="!isValid" :loading="loading" @click="validate()">Submit</n-button>
			</div>
		</div>
	</div>
</template>

<script setup lang="ts">
import type { FormInst, FormRules, FormValidationError } from "naive-ui"
import type { IncidentNotificationPayload } from "@/api/endpoints/incidentManagement/notification"
import type { IncidentNotification } from "@/types/incidentManagement/notifications.d"
import { NButton, NForm, NFormItem, NInput, NSpin, NSwitch, useMessage } from "naive-ui"
import { computed, onMounted, ref, watch } from "vue"
import Api from "@/api"

interface IncidentNotificationForm {
	shuffle_workflow_id: string
	enabled: boolean
}

const { incidentNotification, customerCode } = defineProps<{
	incidentNotification?: IncidentNotification
	customerCode: string
}>()

const emit = defineEmits<{
	(e: "submitted", value: IncidentNotification): void
	(e: "startLoading"): void
	(e: "stopLoading"): void
	(
		e: "mounted",
		value: {
			reset: () => void
		}
	): void
}>()

const message = useMessage()
const form = ref<IncidentNotificationForm>(getClearForm(incidentNotification))
const formRef = ref<FormInst | null>(null)
const loading = ref(false)

const isValid = computed(() => {
	return !!form.value.shuffle_workflow_id
})

const rules: FormRules = {
	shuffle_workflow_id: {
		required: true,
		message: "Please insert Shuffle Workflow Id",
		trigger: ["input", "blur"]
	}
}

watch(loading, val => {
	if (val) {
		emit("startLoading")
	} else {
		emit("stopLoading")
	}
})

function getClearForm(incidentNotification?: IncidentNotification): IncidentNotificationForm {
	return {
		shuffle_workflow_id: incidentNotification?.shuffle_workflow_id ?? "",
		enabled: incidentNotification?.enabled ?? false
	}
}

function reset(incidentNotification?: IncidentNotification) {
	if (!loading.value) {
		resetForm(incidentNotification)
		formRef.value?.restoreValidation()
	}
}

function resetForm(incidentNotification?: IncidentNotification) {
	form.value = getClearForm(incidentNotification)
}

function validate() {
	if (!formRef.value) return

	formRef.value.validate((errors?: Array<FormValidationError>) => {
		if (!errors) {
			submit()
		} else {
			message.warning("You must fill in the required fields correctly.")
			return false
		}
	})
}

function submit() {
	loading.value = true

	const payload: IncidentNotificationPayload = {
		customer_code: customerCode,
		shuffle_workflow_id: form.value.shuffle_workflow_id,
		enabled: form.value.enabled
	}

	Api.incidentManagement.notification
		.setNotification(payload)
		.then(res => {
			if (res.data.success) {
				message.success(res.data?.message || "Notification saved successfully")
				emit("submitted", { ...payload, id: incidentNotification?.id || 0 })
			} else {
				message.warning(res.data?.message || "An error occurred. Please try again later.")
			}
		})
		.catch(err => {
			message.error(err.response?.data?.message || "An error occurred. Please try again later.")
		})
		.finally(() => {
			loading.value = false
		})
}

onMounted(() => {
	emit("mounted", {
		reset
	})
})
</script>
