<template>
	<n-spin :show="loading" class="custom-alert-form">
		<n-form :label-width="80" :model="form" :rules="rules" ref="formRef">
			<div class="flex flex-col gap-2">
				<div class="flex gap-4">
					<n-form-item label="Priority" path="alert_priority" class="w-28">
						<n-select
							v-model:value="form.alert_priority"
							:options="alertPriorityOptions"
							placeholder="Select..."
							clearable
						/>
					</n-form-item>
					<n-form-item label="Name" path="alert_name" class="grow">
						<n-input
							v-model:value.trim="form.alert_name"
							placeholder="Please insert Alert Name"
							clearable
						/>
					</n-form-item>
				</div>
				<div class="flex flex-col gap-2">
					<n-form-item label="Description" path="alert_description">
						<n-input
							v-model:value.trim="form.alert_description"
							placeholder="Please insert Alert Description"
							clearable
							type="textarea"
							:autosize="{
								minRows: 3,
								maxRows: 10
							}"
						/>
					</n-form-item>
					<n-form-item label="Search Query" path="search_query">
						<n-input
							v-model:value.trim="form.search_query"
							placeholder="Please insert Search Query"
							clearable
						/>
					</n-form-item>
				</div>
				<div class="custom-fields-editor">
					<n-form-item label="Custom fields" required path="custom_fields">
						<div class="custom-fields-list flex flex-col gap-4">
							<n-card size="small" v-for="cf of form.custom_fields" :key="cf.key">
								<div class="custom-field-box flex gap-2">
									<n-form-item label="Name" class="grow" size="small">
										<n-input
											v-model:value.trim="cf.name"
											placeholder="Custom field Name"
											clearable
										/>
									</n-form-item>
									<n-form-item label="Value" class="grow" size="small">
										<n-input
											v-model:value.trim="cf.value"
											placeholder="Custom field Value"
											clearable
										/>
									</n-form-item>
									<n-form-item size="small">
										<n-button type="error" secondary>
											<template #icon>
												<Icon :name="RemoveIcon"></Icon>
											</template>
										</n-button>
									</n-form-item>
								</div>
							</n-card>
							<div>
								<n-button @click="addCustomFiled()">
									<template #icon>
										<Icon :name="AddIcon"></Icon>
									</template>
									Add Custom Field
								</n-button>
							</div>
						</div>
					</n-form-item>
				</div>
				<div class="flex gap-4">
					<n-form-item label="Search within (seconds)" path="search_within_seconds" class="grow">
						<n-input-number
							:min="1"
							v-model:value="form.search_within_seconds"
							placeholder="Input time in seconds"
							clearable
							class="w-full"
						/>
					</n-form-item>
					<n-form-item label="Execute every (seconds)" path="execute_every_seconds" class="grow">
						<n-input-number
							:min="1"
							v-model:value="form.execute_every_seconds"
							placeholder="Input time in seconds"
							clearable
							class="w-full"
						/>
					</n-form-item>
				</div>
				<div class="flex justify-between gap-4">
					<div class="flex gap-4">
						<slot name="additionalActions"></slot>
					</div>
					<div class="flex gap-4">
						<n-button @click="reset()" :disabled="loading">Reset</n-button>
						<n-button
							type="primary"
							:disabled="!isValid"
							@click="validate()"
							:loading="submittingCustomAlert"
						>
							Submit
						</n-button>
					</div>
				</div>
			</div>
		</n-form>
	</n-spin>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from "vue"
import Api from "@/api"
import {
	useMessage,
	NForm,
	NFormItem,
	NInput,
	NButton,
	NSpin,
	NSelect,
	NInputNumber,
	NCard,
	type FormValidationError,
	type FormInst,
	type FormRules,
	type FormItemRule
} from "naive-ui"
import _trim from "lodash/trim"
import _get from "lodash/get"
import _toSafeInteger from "lodash/toSafeInteger"
import { type CustomProvisionPayload, CustomProvisionPriority } from "@/api/monitoringAlerts"
import Icon from "@/components/common/Icon.vue"

interface CustomProvisionForm {
	alert_name: string
	alert_description: string
	alert_priority: null | CustomProvisionPriority
	search_query: string
	custom_fields: {
		name: string
		value: string
		key: number
	}[]
	search_within_seconds: number
	execute_every_seconds: number
}

const emit = defineEmits<{
	(e: "update:loading", value: boolean): void
	(
		e: "mounted",
		value: {
			reset: () => void
		}
	): void
}>()

const RemoveIcon = "ph:trash"
const AddIcon = "carbon:add-alt"
const submittingCustomAlert = ref(false)
const loading = computed(() => submittingCustomAlert.value)
const message = useMessage()
const form = ref<CustomProvisionForm>(getClearForm())
const formRef = ref<FormInst | null>(null)

const alertPriorityOptions: { label: string; value: CustomProvisionPriority }[] = [
	{ label: "Low", value: CustomProvisionPriority.LOW },
	{ label: "Medium", value: CustomProvisionPriority.MEDIUM },
	{ label: "High", value: CustomProvisionPriority.HIGH }
]

const rules: FormRules = {
	alert_priority: {
		required: true,
		validator: validatorNumber("Alert Priority", "Required"),
		trigger: ["input", "blur"]
	},
	alert_name: {
		required: true,
		message: "Please input the Alert Name",
		trigger: ["input", "blur"]
	},
	alert_description: {
		required: true,
		message: "Please input the Alert Description",
		trigger: ["input", "blur"]
	},
	search_query: {
		required: true,
		message: "Please input the Search Query",
		trigger: ["input", "blur"]
	},
	search_within_seconds: {
		required: true,
		// message: "Please input Search within",
		validator: validatorNumber("Search within"),
		trigger: ["input", "blur"]
	},
	execute_every_seconds: {
		required: true,
		// message: "Please input Execute every",
		validator: validatorNumber("Execute every"),
		trigger: ["input", "blur"]
	}
}

const isValid = computed(() => {
	let valid = true

	for (const key in rules) {
		const rule = rules[key] as FormRules

		if (rule.required && !_trim(_get(form.value, key))) {
			valid = false
		}
	}

	return valid
})

function validatorNumber(fieldName: string, defaultMessage?: string) {
	return (rule: FormItemRule, value: string) => {
		if (!value) {
			return new Error(defaultMessage || `${fieldName} is required`)
		} else if (!/^\d*$/.test(value)) {
			return new Error(`${fieldName} should be an integer`)
		} else if (Number(value) < 1) {
			return new Error(`${fieldName} should be above 1`)
		}
		return true
	}
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

function addCustomFiled() {
	form.value.custom_fields.push({
		name: "",
		value: "",
		key: new Date().getTime()
	})
}

function getClearForm(): CustomProvisionForm {
	return {
		alert_name: "",
		alert_description: "",
		alert_priority: null,
		search_query: "",
		custom_fields: [],
		search_within_seconds: 1,
		execute_every_seconds: 1
	}
}

function reset() {
	if (!loading.value) {
		form.value = getClearForm()
		formRef.value?.restoreValidation()
	}
}

function submit() {
	submittingCustomAlert.value = true

	const payload: CustomProvisionPayload = {
		alert_name: _trim(form.value.alert_name),
		alert_description: _trim(form.value.alert_description),
		alert_priority: form.value.alert_priority as CustomProvisionPriority,
		search_query: _trim(form.value.search_query),
		custom_fields: form.value.custom_fields,
		search_within_ms: _toSafeInteger(form.value.search_within_seconds) * 1000,
		execute_every_ms: _toSafeInteger(form.value.execute_every_seconds) * 1000,
		streams: []
	}

	Api.monitoringAlerts
		.customProvision(payload)
		.then(res => {
			if (res.data.success) {
				// TODO: check default message
				message.success(res.data?.message || "Customer Alert created successfully")
			} else {
				message.warning(res.data?.message || "An error occurred. Please try again later.")
			}
		})
		.catch(err => {
			message.error(err.response?.data?.message || "An error occurred. Please try again later.")
		})
		.finally(() => {
			submittingCustomAlert.value = false
		})
}

watch(loading, val => {
	emit("update:loading", val)
})

onMounted(() => {
	emit("mounted", {
		reset
	})
})
</script>

<style lang="scss" scoped>
.custom-alert-form {
	.custom-fields-editor {
		width: 100%;

		.custom-fields-list {
			width: 100%;

			.custom-field-box {
				width: 100%;
			}
		}
	}
}
</style>
