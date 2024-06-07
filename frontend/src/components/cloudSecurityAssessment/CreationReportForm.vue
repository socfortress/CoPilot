<template>
	<n-spin :show="loading" class="creation-report-form">
		<n-form :label-width="80" :model="form" :rules="rules" ref="formRef">
			<div class="flex flex-col gap-2">
				<div class="flex gap-4 items-start">
					<n-form-item label="Type" path="report_type" class="w-32">
						<n-select
							v-model:value="form.report_type"
							:options="reportTypeOptions"
							placeholder="Select..."
							clearable
							:loading="loadingOptions"
						/>
					</n-form-item>
					<n-form-item label="Name" path="report_name" class="grow">
						<n-input
							v-model:value.trim="form.report_name"
							placeholder="Please insert Report Name"
							clearable
						/>
					</n-form-item>
				</div>
				<div class="flex flex-col gap-2">
					<n-form-item label="Access Key ID" path="access_key_id">
						<n-input
							v-model:value.trim="form.access_key_id"
							placeholder="Please insert Access Key ID"
							clearable
						/>
					</n-form-item>
					<n-form-item label="Secret Access Key" path="secret_access_key">
						<n-input
							v-model:value.trim="form.secret_access_key"
							placeholder="Please insert Secret Access Key"
							type="password"
							show-password-on="click"
							clearable
						/>
					</n-form-item>
				</div>

				<div class="flex justify-between gap-4">
					<n-button @click="reset()" :disabled="loading">Reset</n-button>
					<n-button
						type="primary"
						:disabled="!isValid"
						@click="validate(() => submit())"
						:loading="submitting"
					>
						Submit
					</n-button>
				</div>
			</div>
		</n-form>
	</n-spin>
</template>

<script setup lang="ts">
import { computed, onBeforeMount, onMounted, ref } from "vue"
import Api from "@/api"
import {
	useMessage,
	NForm,
	NFormItem,
	NInput,
	NButton,
	NSpin,
	NSelect,
	type FormValidationError,
	type FormInst,
	type FormRules,
	type MessageReactive
} from "naive-ui"
import type { ScoutSuiteReportPayload } from "@/types/cloudSecurityAssessment.d"

type FormPayload = Omit<ScoutSuiteReportPayload, "report_type"> & { report_type: string | null }

const emit = defineEmits<{
	(e: "submitted"): void
	(
		e: "mounted",
		value: {
			reset: () => void
		}
	): void
}>()

const submitting = ref(false)
const loadingOptions = ref(false)
const loading = computed(() => submitting.value || loadingOptions.value)
const message = useMessage()
const form = ref<FormPayload>(getClearForm())
const formRef = ref<FormInst | null>(null)

const availableTypes = ["aws"]

const reportTypeOptions = ref<{ label: string; value: string; disabled: boolean }[]>([])

const rules: FormRules = {
	report_type: {
		required: true,
		message: "Please input the Report Type",
		trigger: ["input", "blur"]
	},
	access_key_id: {
		required: true,
		message: "Please input the Access Key ID",
		trigger: ["input", "blur"]
	},
	secret_access_key: {
		required: true,
		message: "Please input the Secret Access Key",
		trigger: ["input", "blur"]
	},
	report_name: {
		required: true,
		message: "Please input the Report Name",
		trigger: ["input", "blur"]
	}
}

let validationMessage: MessageReactive | null = null

const isValid = computed(() => {
	if (!form.value.access_key_id) {
		return false
	}
	if (!form.value.secret_access_key) {
		return false
	}
	if (!form.value.report_type) {
		return false
	}
	if (!form.value.report_name) {
		return false
	}

	return true
})

function validate(cb?: () => void) {
	if (!formRef.value) return

	formRef.value.validate((errors?: Array<FormValidationError>) => {
		if (!errors) {
			validationMessage?.destroy()
			validationMessage = null
			if (cb) cb()
		} else {
			if (!validationMessage) {
				validationMessage = message.warning("You must fill in the required fields correctly.")
			}
			return false
		}
	})
}

function getClearForm(): FormPayload {
	return {
		report_type: null,
		access_key_id: "",
		secret_access_key: "",
		report_name: ""
	}
}

function reset() {
	if (!loading.value) {
		resetForm()
		formRef.value?.restoreValidation()
	}
}

function resetForm() {
	form.value = getClearForm()
}

function submit() {
	const method = form.value.report_type === "aws" ? "generateAwsScoutSuiteReport" : null

	if (!method) {
		return
	}

	submitting.value = true

	const payload: ScoutSuiteReportPayload = {
		...form.value,
		report_type: form.value.report_type || ""
	}

	Api.cloudSecurityAssessment[method](payload)
		.then(res => {
			if (res.data.success) {
				message.success(res.data?.message || `ScoutSuite report generation started successfully`, {
					duration: 10 * 1000
				})
				emit("submitted")
				resetForm()
			} else {
				message.warning(res.data?.message || "An error occurred. Please try again later.")
			}
		})
		.catch(err => {
			message.error(err.response?.data?.message || "An error occurred. Please try again later.")
		})
		.finally(() => {
			submitting.value = false
		})
}

function getScoutSuiteReportGenerationOptions() {
	loadingOptions.value = true

	Api.cloudSecurityAssessment
		.getScoutSuiteReportGenerationOptions()
		.then(res => {
			if (res.data.success) {
				reportTypeOptions.value = (res.data?.options || []).map(o => ({
					label: o.toUpperCase(),
					value: o,
					disabled: !availableTypes.includes(o)
				}))
			} else {
				message.warning(res.data?.message || "An error occurred. Please try again later.")
			}
		})
		.catch(err => {
			message.error(err.response?.data?.message || "An error occurred. Please try again later.")
		})
		.finally(() => {
			loadingOptions.value = false
		})
}

onBeforeMount(() => {
	getScoutSuiteReportGenerationOptions()
})

onMounted(() => {
	emit("mounted", {
		reset
	})
})
</script>
