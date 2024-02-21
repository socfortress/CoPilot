<template>
	<div class="active-response-invoke-form flex flex-col justify-between grow">
		<div class="form-box">
			<n-spin v-model:show="loading">
				<n-form :label-width="80" :model="form" :rules="rules" ref="formRef">
					<div class="grid gap-6 grid-auto-flow-200">
						<n-form-item label="Action" path="action">
							<n-select v-model:value="form.action" :options="invokeActionOptions" />
						</n-form-item>
						<n-form-item label="IP Address" path="ip">
							<n-input v-model:value.trim="form.ip" placeholder="Input the IP Address..." />
						</n-form-item>
					</div>
				</n-form>
				<p v-if="agentId">
					This action will be submitted only for the Agent:
					<code>{{ agentId }}</code>
				</p>
			</n-spin>
		</div>
		<div class="buttons-box flex justify-end gap-3">
			<n-button @click="close()" secondary>Close</n-button>
			<n-button type="primary" :disabled="!isValid" @click="validate()" :loading="loading">Submit</n-button>
		</div>
	</div>
</template>

<script setup lang="ts">
import {
	NButton,
	NForm,
	NFormItem,
	NInput,
	NSelect,
	NSpin,
	type FormItemRule,
	type FormRules,
	type FormInst,
	type FormValidationError,
	useMessage
} from "naive-ui"
import { computed, ref } from "vue"
import { watch } from "vue"
import type { SupportedActiveResponse } from "@/types/activeResponse"
import isIP from "validator/es/lib/isIP"
import type { InvokeRequest, InvokeRequestAction } from "@/api/activeResponse"
import Api from "@/api"

interface InvokeForm {
	action: null | InvokeRequestAction
	ip: string
}

const emit = defineEmits<{
	(e: "close"): void
	(e: "submitted"): void
	(e: "startLoading"): void
	(e: "stopLoading"): void
}>()

const { activeResponse, agentId } = defineProps<{
	activeResponse: SupportedActiveResponse
	agentId?: string | number
}>()

const message = useMessage()
const form = ref<InvokeForm>(getClearForm())
const formRef = ref<FormInst | null>(null)
const invokeActionOptions = [
	{ label: "Block", value: "block" },
	{ label: "Unblock", value: "unblock" }
]
const isValid = computed(() => {
	return !!form.value.action && isIP(form.value.ip)
})
const loading = ref(false)

watch(loading, val => {
	if (val) {
		emit("startLoading")
	} else {
		emit("stopLoading")
	}
})

const rules: FormRules = {
	action: {
		required: true,
		message: "Please Select an Action",
		trigger: ["input", "blur"]
	},
	ip: {
		required: true,
		validator: validateIp,
		trigger: ["blur"]
	}
}

function validateIp(rule: FormItemRule, value: string) {
	if (!value || !isIP(value)) {
		return new Error("Please input a valid IP Address")
	}

	return true
}

function getClearForm(): InvokeForm {
	return {
		action: null,
		ip: ""
	}
}

function close() {
	reset()
	emit("close")
}

function reset() {
	form.value = getClearForm()
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

	const payload: InvokeRequest = {
		activeResponseName: activeResponse.name,
		action: form.value.action as InvokeRequestAction,
		ip: form.value.ip
	}

	if (agentId) {
		payload.agentId = agentId.toString()
	}

	Api.activeResponse
		.invoke(payload)
		.then(res => {
			if (res.data.success) {
				message.success(res.data?.message || "Active Response invoked successfully")
				emit("submitted")
				reset()
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
</script>
