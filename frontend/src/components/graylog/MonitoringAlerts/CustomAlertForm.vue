<template>
	<n-spin :show="loading" class="customer-provisioning-default-settings-form">
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
						<n-input v-model:value.trim="form.alert_name" placeholder="Please inset Alert Name" clearable />
					</n-form-item>
				</div>
				<div class="flex flex-col gap-2">
					<n-form-item label="Description" path="alert_description">
						<n-input
							v-model:value.trim="form.alert_description"
							placeholder="Please inset Alert Description"
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
							placeholder="Please inset Search Query"
							clearable
						/>
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
	type FormValidationError,
	type FormInst,
	type FormRules
} from "naive-ui"
import _trim from "lodash/trim"
import _get from "lodash/get"
import _toSafeInteger from "lodash/toSafeInteger"
import { type CustomProvisionPayload, CustomProvisionPriority } from "@/api/monitoringAlerts"

interface CustomProvisionForm {
	alert_name: string
	alert_description: string
	alert_priority: null | CustomProvisionPriority
	search_query: string
	custom_fields: {
		name: string
		value: string
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
		message: "Please input the Alert Priority",
		trigger: ["input", "blur"]
	},
	alert_name: {
		required: true,
		message: "Please input the Alert Name",
		trigger: ["input", "blur"]
	},
	alert_description: {
		required: true,
		message: "Please input the Alert Name",
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
