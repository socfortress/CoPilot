<template>
	<div class="customer-ai-triggers-form flex grow flex-col justify-between">
		<div class="form-box">
			<n-spin v-model:show="loading">
				<n-form :label-width="80" :model="form">
					<n-form-item label="Enabled" path="enabled">
						<n-switch v-model:value="form.enabled" />
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
				<n-button type="primary" :loading @click="submit()">Submit</n-button>
			</div>
		</div>
	</div>
</template>

<script setup lang="ts">
import type { AITriggerPayload } from "@/api/endpoints/incidentManagement/ai-triggers"
import type { ApiError } from "@/types/common"
import type { AITrigger } from "@/types/incidentManagement/ai-triggers"
import { NButton, NForm, NFormItem, NSpin, NSwitch, useMessage } from "naive-ui"
import { ref, watch } from "vue"
import Api from "@/api"
import { getApiErrorMessage } from "@/utils"

interface AITriggerForm {
	enabled: boolean
}

const { aiTrigger, customerCode } = defineProps<{
	aiTrigger?: AITrigger
	customerCode: string
}>()

const emit = defineEmits<{
	(e: "submitted", value: AITrigger): void
	(e: "startLoading"): void
	(e: "stopLoading"): void
}>()

const message = useMessage()
const form = ref<AITriggerForm>(getClearForm(aiTrigger))
const loading = ref(false)

watch(loading, val => {
	if (val) {
		emit("startLoading")
	} else {
		emit("stopLoading")
	}
})

function getClearForm(aiTrigger?: AITrigger): AITriggerForm {
	return {
		enabled: aiTrigger?.enabled ?? false
	}
}

function reset(aiTrigger?: AITrigger) {
	if (!loading.value) {
		form.value = getClearForm(aiTrigger)
	}
}

function submit() {
	loading.value = true

	const payload: AITriggerPayload = {
		customer_code: customerCode,
		enabled: form.value.enabled
	}

	Api.incidentManagement.aiTriggers
		.setAITrigger(payload)
		.then(res => {
			if (res.data.success) {
				message.success(res.data?.message || "AI Trigger saved successfully")
				emit("submitted", { ...payload, id: aiTrigger?.id || 0 })
			} else {
				message.warning(res.data?.message || "An error occurred. Please try again later.")
			}
		})
		.catch(err => {
			message.error(getApiErrorMessage(err as ApiError) || "An error occurred. Please try again later.")
		})
		.finally(() => {
			loading.value = false
		})
}

defineExpose({
	reset
})
</script>
