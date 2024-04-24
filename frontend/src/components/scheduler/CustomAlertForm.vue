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
					<n-form-item label="Custom fields" path="custom_fields">
						<div class="custom-fields-list flex flex-col gap-1">
							<n-card size="small" v-for="(cf, index) of form.custom_fields" :key="cf.key">
								<div class="custom-field-box flex gap-2">
									<n-form-item
										label="Name"
										class="grow"
										size="small"
										:path="`custom_fields[${index}].name`"
										:rule="{
											required: true,
											message: `Field Name required`,
											trigger: ['input', 'blur']
										}"
									>
										<n-input
											v-model:value.trim="cf.name"
											@update:value="validate()"
											placeholder="Custom field Name"
											clearable
										/>
									</n-form-item>
									<n-form-item
										label="Value"
										class="grow"
										size="small"
										:path="`custom_fields[${index}].value`"
										:rule="{
											required: true,
											message: `Field Value required`,
											trigger: ['input', 'blur']
										}"
									>
										<n-input
											v-model:value.trim="cf.value"
											@update:value="validate()"
											placeholder="Custom field Value"
											clearable
										/>
									</n-form-item>
									<n-form-item size="small">
										<n-button type="error" secondary @click="removeCustomFiled(cf.key)">
											<template #icon>
												<Icon :name="RemoveIcon" :size="16"></Icon>
											</template>
										</n-button>
									</n-form-item>
								</div>
							</n-card>
							<div class="mt-3">
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
							@click="validate(() => submit())"
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
	type FormItemRule,
	type MessageReactive
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
	},
	custom_fields: {
		required: true,
		validator(rule: FormItemRule, value: string) {
			if (!areAllCustomerFieldsFilled.value) {
				return new Error(`Please fill all customer fields`)
			}

			if (!areAllCustomerFieldsUniques.value) {
				return new Error(`There are duplicated fields`)
			}

			if (!value.length || !isCustomerCodePresent.value) {
				return new Error(`At least one custom field with name CUSTOMER_CODE is required`)
			}
			return true
		},
		trigger: ["input", "blur"]
	}
}

const areAllCustomerFieldsFilled = computed(() => {
	const fieldsFilled = form.value.custom_fields.filter(o => !!o.name && !!o.value)

	return fieldsFilled.length === form.value.custom_fields.length
})

const areAllCustomerFieldsUniques = computed(() => {
	const fieldsFilled = form.value.custom_fields.filter(o => !!o.name).map(o => o.name)

	const uniques: string[] = fieldsFilled.filter((value, index, self) => self.indexOf(value) === index)

	return uniques.length === form.value.custom_fields.length
})

const isCustomerCodePresent = computed(() => {
	const field = form.value.custom_fields.filter(o => o.name === "CUSTOMER_CODE" && !!o.value)

	return !!field.length
})

const isValid = computed(() => {
	if (!areAllCustomerFieldsFilled.value) {
		return false
	}

	if (!isCustomerCodePresent.value) {
		return false
	}

	if (!areAllCustomerFieldsUniques.value) {
		return false
	}

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

let validationMessage: MessageReactive | null = null

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

function addCustomFiled() {
	form.value.custom_fields.push({
		name: "",
		value: "",
		key: new Date().getTime()
	})
}

function removeCustomFiled(key: number) {
	form.value.custom_fields = form.value.custom_fields.filter(o => o.key !== key)
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
		resetForm()
		formRef.value?.restoreValidation()
	}
}

function resetForm() {
	form.value = getClearForm()
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
				message.success(
					res.data?.message || `Monitoring alert "${payload.alert_name}" provisioned successfully`
				)
				resetForm()
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

			.n-card {
				background-color: var(--bg-secondary-color);
			}

			.custom-field-box {
				width: 100%;
			}
		}
	}
}
</style>
