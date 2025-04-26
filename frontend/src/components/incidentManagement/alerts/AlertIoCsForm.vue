<template>
	<n-spin :show="submitting" class="flex min-h-48 grow flex-col" content-class="flex grow flex-col gap-4">
		<n-form ref="formRef" :label-width="80" :model="form" :rules="rules">
			<div class="flex flex-col gap-3">
				<div>
					<n-form-item label="Description" path="ioc_description">
						<n-input
							v-model:value.trim="form.ioc_description"
							placeholder="Input the description..."
							clearable
							type="textarea"
							:autosize="{
								minRows: 5,
								maxRows: 15
							}"
						/>
					</n-form-item>
				</div>
				<div class="flex flex-col gap-3 sm:flex-row">
					<n-form-item label="Type" path="ioc_type" class="basis-1/2">
						<n-select
							v-model:value="form.ioc_type"
							:options="iocTypeOptions"
							placeholder="Select the Type..."
							clearable
							to="body"
							@update:value="form.ioc_value && validate()"
						/>
					</n-form-item>
					<n-form-item label="Value" path="ioc_value" class="basis-1/2">
						<n-input
							v-model:value.trim="form.ioc_value"
							:disabled="!form.ioc_type"
							placeholder="Input the value..."
							clearable
						/>
					</n-form-item>
				</div>

				<div class="flex justify-between gap-4">
					<div class="flex gap-4">
						<slot name="additionalActions"></slot>
					</div>
					<div class="flex gap-4">
						<n-button :disabled="submitting" @click="reset()">Reset</n-button>
						<n-button :disabled="!isValid" :loading="submitting" type="primary" @click="validate(submit)">
							Submit
						</n-button>
					</div>
				</div>
			</div>
		</n-form>
	</n-spin>
</template>

<script setup lang="ts">
import type { AlertIocPayload } from "@/api/endpoints/incidentManagement/alerts"
import type { DeepNullable } from "@/types/common"
import type { AlertIOC } from "@/types/incidentManagement/alerts.d"
import type { FormInst, FormItemRule, FormRules, FormValidationError } from "naive-ui"
import Api from "@/api"
import _get from "lodash/get"
import _trim from "lodash/trim"
import { NButton, NForm, NFormItem, NInput, NSelect, NSpin, useMessage } from "naive-ui"
import isIP from "validator/es/lib/isIP"
import isURL from "validator/es/lib/isURL"
import { computed, onMounted, ref, toRefs, watch } from "vue"

const props = defineProps<{ alertId: number }>()
const emit = defineEmits<{
	(e: "update:loading", value: boolean): void
	(e: "submitted", value: AlertIOC): void
	(
		e: "mounted",
		value: {
			reset: () => void
		}
	): void
}>()

const { alertId } = toRefs(props)
const submitting = ref(false)
const message = useMessage()
const form = ref<DeepNullable<AlertIocPayload>>(getForm())
const formRef = ref<FormInst | null>(null)

const rules: FormRules = {
	ioc_value: {
		validator: validateValue,
		required: true,
		trigger: ["input", "blur"]
	},
	ioc_type: {
		message: "Please input the Type",
		required: true,
		trigger: ["input", "blur"]
	},
	ioc_description: {
		message: "Please input the Description",
		required: true,
		trigger: ["input", "blur"]
	}
}

const iocTypeOptions: { label: string; value: string }[] = [
	{ label: "IP", value: "IP" },
	{ label: "DOMAIN", value: "DOMAIN" },
	{ label: "HASH", value: "HASH" },
	{ label: "URL", value: "URL" }
]

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

function validateValue(_rule: FormItemRule, value: string) {
	if (!value) {
		return new Error("Please input a valid Value")
	}

	switch (form.value.ioc_type) {
		case "URL":
			if (!isURL(value, { require_tld: false })) {
				return new Error("Please input a valid URL")
			}
			break
		case "DOMAIN":
			if (!isURL(value, { require_tld: false })) {
				return new Error("Please input a valid DOMAIN")
			}
			break
		case "IP":
			if (!isIP(value)) {
				return new Error("Please input a valid IP Address")
			}
			break
	}

	return true
}

function validate(cb?: () => void) {
	if (!formRef.value) return

	formRef.value.validate((errors?: Array<FormValidationError>) => {
		if (!errors) {
			if (cb && typeof cb === "function") {
				cb()
			}
		} else {
			message.warning("You must fill in the required fields correctly.")
			return false
		}
	})
}

function getForm() {
	const payload = {
		alert_id: alertId.value,
		ioc_value: null,
		ioc_type: null,
		ioc_description: null
	}
	return payload
}

function reset(force?: boolean) {
	if (!submitting.value || force) {
		resetForm()
		formRef.value?.restoreValidation()
	}
}

function resetForm() {
	form.value = getForm()
}

function submit() {
	submitting.value = true

	Api.incidentManagement.alerts
		.createAlertIoc(form.value as AlertIocPayload)
		.then(res => {
			if (res.data.success) {
				emit("submitted", {
					id: res.data.alert_ioc.ioc_id,
					description: form.value.ioc_description || "",
					type: form.value.ioc_type || "",
					value: form.value.ioc_value || ""
				})
				reset()
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

watch(submitting, val => {
	emit("update:loading", val)
})

onMounted(() => {
	emit("mounted", {
		reset
	})
})
</script>
