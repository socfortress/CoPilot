<template>
	<n-spin :show="loading" class="customer-provisioning-default-settings-form">
		<n-form ref="formRef" :label-width="80" :model="form" :rules="rules">
			<div class="flex flex-col gap-3">
				<div>
					<n-form-item label="Name" path="case_name">
						<n-input v-model:value.trim="form.case_name" placeholder="Input the case name..." clearable />
					</n-form-item>
				</div>
				<div>
					<n-form-item label="Description" path="case_description">
						<n-input
							v-model:value.trim="form.case_description"
							placeholder="Input the case description..."
							clearable
							type="textarea"
							:autosize="{
								minRows: 5,
								maxRows: 15,
							}"
						/>
					</n-form-item>
				</div>
				<div class="flex gap-3">
					<n-form-item label="Status" path="case_status" class="basis-1/2">
						<n-select
							v-model:value="form.case_status"
							:options="statusOptions"
							placeholder="Value..."
							clearable
							to="body"
						/>
					</n-form-item>
					<n-form-item label="Assigned user" path="assigned_to" class="basis-1/2">
						<n-select
							v-model:value="form.assigned_to"
							:options="usersOptions"
							placeholder="Value..."
							clearable
							to="body"
						/>
					</n-form-item>
				</div>

				<div class="flex justify-between gap-4">
					<div class="flex gap-4">
						<slot name="additionalActions"></slot>
					</div>
					<div class="flex gap-4">
						<n-button :disabled="loading" @click="reset()">Reset</n-button>
						<n-button type="primary" :disabled="!isValid" :loading="submitting" @click="validate()">
							Submit
						</n-button>
					</div>
				</div>
			</div>
		</n-form>
	</n-spin>
</template>

<script setup lang="ts">
import type { AlertStatus } from "@/types/incidentManagement/alerts.d"
import type { Case, CasePayload } from "@/types/incidentManagement/cases.d"
import Api from "@/api"
import _get from "lodash/get"
import _trim from "lodash/trim"
import {
	type FormInst,
	type FormRules,
	type FormValidationError,
	NButton,
	NForm,
	NFormItem,
	NInput,
	NSelect,
	NSpin,
	useMessage
} from "naive-ui"
import { computed, inject, onBeforeMount, onMounted, ref, type Ref, watch } from "vue"

const emit = defineEmits<{
	(e: "update:loading", value: boolean): void
	(e: "submitted", value: Case): void
	(
		e: "mounted",
		value: {
			load: () => void
		}
	): void
}>()

const loadingAvailableUsers = ref(false)
const submitting = ref(false)
const loading = computed(() => loadingAvailableUsers.value || submitting.value)
const message = useMessage()
const form = ref<CasePayload>(getForm())
const formRef = ref<FormInst | null>(null)
const availableUsers = inject<Ref<string[]>>("assignable-users", ref([]))

const rules: FormRules = {
	case_name: {
		message: "Please input the Name",
		required: true,
		trigger: ["input", "blur"]
	},
	case_description: {
		message: "Please input the Description",
		required: true,
		trigger: ["input", "blur"]
	},
	assigned_to: {
		message: "Please input the Assigned user",
		required: true,
		trigger: ["input", "blur"]
	},
	case_status: {
		message: "Please input the Status",
		required: true,
		trigger: ["input", "blur"]
	}
}

const statusOptions: { label: string; value: AlertStatus }[] = [
	{ label: "Open", value: "OPEN" },
	{ label: "Closed", value: "CLOSED" },
	{ label: "In progress", value: "IN_PROGRESS" }
]

const usersOptions = computed(() => availableUsers.value.map(o => ({ label: o, value: o })))

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

function getForm() {
	const payload = {
		case_name: "",
		case_creation_time: new Date(),
		case_description: "",
		assigned_to: null,
		case_status: null
	}
	return payload
}

function reset(force?: boolean) {
	if (!loading.value || force) {
		resetForm()
		formRef.value?.restoreValidation()
	}
}

function resetForm() {
	form.value = getForm()
}

function submit() {
	submitting.value = true

	Api.incidentManagement
		.createCase(form.value)
		.then(res => {
			if (res.data.success) {
				message.success(res.data?.message || "Case created successfully")
				reset(true)
				emit("submitted", res.data.case)
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

function getAvailableUsers() {
	loadingAvailableUsers.value = true

	Api.incidentManagement
		.getAvailableUsers()
		.then(res => {
			if (res.data.success) {
				availableUsers.value = res.data?.available_users || []
			} else {
				message.warning(res.data?.message || "An error occurred. Please try again later.")
			}
		})
		.catch(err => {
			message.error(err.response?.data?.message || "An error occurred. Please try again later.")
		})
		.finally(() => {
			loadingAvailableUsers.value = false
		})
}

function load() {
	if (!availableUsers.value.length) {
		getAvailableUsers()
	}
	reset()
}

watch(loading, val => {
	emit("update:loading", val)
})

onBeforeMount(() => {
	load()
})

onMounted(() => {
	emit("mounted", {
		load
	})
})
</script>
