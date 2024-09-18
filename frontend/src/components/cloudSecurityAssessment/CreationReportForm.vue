<template>
	<n-spin :show="loading" class="creation-report-form">
		<n-form ref="baseFormRef" :model="baseForm" :rules="rules">
			<div class="flex flex-col gap-2">
				<div class="flex gap-4 items-start">
					<n-form-item label="Type" path="report_type" class="w-32">
						<n-select
							v-model:value="baseForm.report_type"
							:options="reportTypeOptions"
							placeholder="Select..."
							clearable
							:loading="loadingOptions"
						/>
					</n-form-item>
					<n-form-item label="Name" path="report_name" class="grow">
						<n-input
							v-model:value.trim="baseForm.report_name"
							placeholder="Please insert Report Name"
							clearable
						/>
					</n-form-item>
				</div>

				<AwsTypeForm
					v-if="baseForm.report_type === ScoutSuiteReportType.AWS"
					@model="typeForm = $event"
					@valid="typeFormValid = $event"
					@mounted="typeFormRef = $event"
				/>

				<AzureTypeForm
					v-if="baseForm.report_type === ScoutSuiteReportType.Azure"
					@model="typeForm = $event"
					@valid="typeFormValid = $event"
					@mounted="typeFormRef = $event"
				/>

				<GcpTypeForm
					v-if="baseForm.report_type === ScoutSuiteReportType.Gcp"
					@model="typeForm = $event"
					@valid="typeFormValid = $event"
					@mounted="typeFormRef = $event"
				/>

				<div class="flex justify-between gap-4 mt-8">
					<n-button :disabled="loading" @click="reset()">Reset</n-button>
					<n-button
						type="primary"
						:disabled="!isValid"
						:loading="submitting"
						@click="validate(() => submit())"
					>
						Submit
					</n-button>
				</div>
			</div>
		</n-form>
	</n-spin>
</template>

<script setup lang="ts">
import type { ApiCommonResponse, ApiError } from "@/types/common.d"
import Api from "@/api"
import {
	type ScoutSuiteAwsReportPayload,
	type ScoutSuiteAzureReportPayload,
	type ScoutSuiteGcpReportPayload,
	type ScoutSuiteReportPayload,
	ScoutSuiteReportType
} from "@/types/cloudSecurityAssessment.d"
import {
	type FormInst,
	type FormRules,
	type FormValidationError,
	type MessageReactive,
	NButton,
	NForm,
	NFormItem,
	NInput,
	NSelect,
	NSpin,
	useMessage
} from "naive-ui"
import { computed, onBeforeMount, onMounted, ref, watch } from "vue"
import AwsTypeForm from "./FormTypes/AwsTypeForm.vue"
import AzureTypeForm from "./FormTypes/AzureTypeForm.vue"
import GcpTypeForm from "./FormTypes/GcpTypeForm.vue"

type BaseFormPayload = Omit<ScoutSuiteReportPayload, "report_type"> & { report_type: ScoutSuiteReportType | null }
type TypeFormPayload = Partial<ScoutSuiteAwsReportPayload | ScoutSuiteAzureReportPayload | ScoutSuiteGcpReportPayload>

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
const baseForm = ref<BaseFormPayload>(getClearBaseForm())
const typeForm = ref<TypeFormPayload | null>(null)
const typeFormValid = ref<boolean>(false)
const baseFormRef = ref<FormInst | null>(null)
const typeFormRef = ref<FormInst | null>(null)

const availableTypes = ["aws", "azure", "gcp"]

const reportTypeOptions = ref<{ label: string; value: string; disabled: boolean }[]>([])

const rules: FormRules = {
	report_type: {
		required: true,
		message: "Please input the Report Type",
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
	if (!baseForm.value.report_type) {
		return false
	}
	if (!baseForm.value.report_name) {
		return false
	}

	if (!typeFormValid.value) {
		return false
	}

	return true
})

watch(
	() => baseForm.value.report_type,
	() => {
		typeForm.value = null
		typeFormRef.value = null
		typeFormValid.value = false
	}
)

function validate(cb?: () => void) {
	if (!baseFormRef.value || !typeFormRef.value) return

	baseFormRef.value.validate((errors?: Array<FormValidationError>) => {
		if (!errors) {
			validationMessage?.destroy()
			validationMessage = null
			;(typeFormRef.value as FormInst).validate((errors?: Array<FormValidationError>) => {
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
		} else {
			if (!validationMessage) {
				validationMessage = message.warning("You must fill in the required fields correctly.")
			}
			return false
		}
	})
}

function getClearBaseForm(): BaseFormPayload {
	return {
		report_type: null,
		report_name: ""
	}
}

function reset() {
	if (!loading.value) {
		resetForm()
		baseFormRef.value?.restoreValidation()
	}
}

function resetForm() {
	baseForm.value = getClearBaseForm()
}

function submit() {
	let apiCall: Promise<ApiCommonResponse> | null = null

	switch (baseForm.value.report_type) {
		case ScoutSuiteReportType.AWS:
			apiCall = Api.cloudSecurityAssessment.generateAwsScoutSuiteReport({
				...baseForm.value,
				report_type: ScoutSuiteReportType.AWS,
				...(typeForm.value as ScoutSuiteAwsReportPayload)
			})
			break
		case ScoutSuiteReportType.Azure:
			apiCall = Api.cloudSecurityAssessment.generateAzureScoutSuiteReport({
				...baseForm.value,
				report_type: ScoutSuiteReportType.Azure,
				...(typeForm.value as ScoutSuiteAzureReportPayload)
			})
			break
		case ScoutSuiteReportType.Gcp:
			apiCall = Api.cloudSecurityAssessment.generateGcpScoutSuiteReport({
				...baseForm.value,
				report_type: ScoutSuiteReportType.Gcp,
				...(typeForm.value as ScoutSuiteGcpReportPayload)
			})
			break
	}

	if (!apiCall) {
		return
	}

	submitting.value = true

	apiCall
		.then(res => {
			if (res.data.success) {
				message.success(
					res.data?.message ||
						`ScoutSuite report generation started successfully. This will take a few minutes to complete. Check back in shortly.`,
					{
						duration: 10 * 1000
					}
				)
				emit("submitted")
				resetForm()
			} else {
				message.warning(res.data?.message || "An error occurred. Please try again later.")
			}
		})
		.catch((err: ApiError) => {
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
