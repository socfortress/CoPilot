<template>
	<n-spin :show="loading" class="job-form">
		<n-form :label-width="80" :model="form" :rules="rules" ref="formRef">
			<div class="flex flex-col gap-1">
				<n-form-item label="Time interval (minutes)" path="time_interval" class="grow">
					<n-input-number
						:min="1"
						v-model:value="form.time_interval"
						placeholder="Input time in minutes"
						clearable
						class="w-full"
					/>
				</n-form-item>

				<div class="flex gap-3 justify-end items-center">
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
import { computed, ref, toRefs } from "vue"
import Api from "@/api"
import {
	useMessage,
	NForm,
	NFormItem,
	NButton,
	NSpin,
	NInputNumber,
	type FormValidationError,
	type FormInst,
	type FormRules,
	type FormItemRule,
	type MessageReactive
} from "naive-ui"
import _trim from "lodash/trim"
import _get from "lodash/get"
import type { UpdateJobPayload } from "@/api/scheduler"
import type { Job } from "@/types/scheduler"

const props = defineProps<{ job: Job }>()
const { job } = toRefs(props)

const emit = defineEmits<{
	(e: "updated", value: UpdateJobPayload): void
}>()

const submitting = ref(false)
const loading = computed(() => submitting.value)
const message = useMessage()
const form = ref<UpdateJobPayload>(getClearForm())
const formRef = ref<FormInst | null>(null)

const rules: FormRules = {
	time_interval: {
		required: true,
		validator: validatorNumber("Alert Priority", "Required"),
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

function getClearForm(): UpdateJobPayload {
	return {
		time_interval: job.value.time_interval || 1,
		extra_data: ""
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
	submitting.value = true

	Api.scheduler
		.updateJob(job.value.id, form.value)
		.then(res => {
			if (res.data.success) {
				message.success(res.data?.message || `Job "${job.value.name}" updated successfully`)
				emit("updated", form.value)
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
</script>
