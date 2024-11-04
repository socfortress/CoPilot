<template>
	<n-spin :show="loading" class="flex min-h-48 grow flex-col" content-class="flex flex-col grow gap-4">
		<div>
			<n-collapse-transition :show="!showForm">
				<n-button v-if="iocs.length" :loading="submitting" type="primary" @click="openForm()">
					<template #icon>
						<Icon :name="AddIcon" />
					</template>
					Create IoC
				</n-button>
			</n-collapse-transition>

			<n-collapse-transition :show="showForm">
				<div class="flex flex-col gap-2">
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
									/>
								</n-form-item>
								<n-form-item label="Value" path="ioc_value" class="basis-1/2">
									<n-input
										v-model:value.trim="form.ioc_value"
										placeholder="Input the value..."
										clearable
									/>
								</n-form-item>
							</div>

							<div class="flex items-center justify-end gap-3">
								<n-button quaternary :disabled="submitting" @click="closeForm()">Close</n-button>

								<n-button :disabled="!isValid" :loading="submitting" type="primary" @click="validate()">
									Submit
								</n-button>
							</div>
						</div>
					</n-form>
				</div>
			</n-collapse-transition>
		</div>

		<div class="flex flex-col gap-2">
			<template v-if="iocs.length">
				<AlertIoCItem v-for="ioc of iocs" :key="ioc.id" :ioc :alert-id embedded @deleted="deleteIoc(ioc)" />
			</template>
			<template v-else>
				<n-collapse-transition :show="!showForm">
					<n-empty v-if="!loading" class="min-h-48">
						<div class="flex flex-col items-center gap-4">
							<p>No IoCs found</p>
							<n-button type="primary" :loading="submitting" @click="openForm()">
								<template #icon>
									<Icon :name="AddIcon" />
								</template>
								Create an IoCs
							</n-button>
						</div>
					</n-empty>
				</n-collapse-transition>
			</template>
		</div>
	</n-spin>
</template>

<script setup lang="ts">
import type { AlertIocPayload } from "@/api/endpoints/incidentManagement"
import type { DeepNullable } from "@/types/common"
import type { AlertIOC } from "@/types/incidentManagement/alerts.d"
import Api from "@/api"
import Icon from "@/components/common/Icon.vue"
import _get from "lodash/get"
import _trim from "lodash/trim"
import {
	type FormInst,
	type FormRules,
	type FormValidationError,
	NButton,
	NCollapseTransition,
	NEmpty,
	NForm,
	NFormItem,
	NInput,
	NSelect,
	NSpin,
	useMessage
} from "naive-ui"
import { computed, ref, toRefs } from "vue"
import AlertIoCItem from "./AlertIoCItem.vue"

const props = defineProps<{ iocs: AlertIOC[]; alertId: number }>()
const emit = defineEmits<{
	(e: "updated", value: AlertIOC[]): void
	(e: "deleted", value: AlertIOC[]): void
}>()

const { iocs, alertId } = toRefs(props)

const AddIcon = "carbon:add-alt"
const iocsList = ref<AlertIOC[]>(iocs.value)
const showForm = ref(false)
const submitting = ref(false)
const deleting = ref(false)
const loading = computed(() => submitting.value || deleting.value)
const message = useMessage()
const form = ref<DeepNullable<AlertIocPayload>>(getForm())
const formRef = ref<FormInst | null>(null)

const rules: FormRules = {
	ioc_value: {
		message: "Please input the Value",
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

function openForm() {
	showForm.value = true
}

function closeForm(doReset?: boolean) {
	showForm.value = false
	if (doReset) {
		reset()
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

function getForm() {
	const payload = {
		alert_id: alertId.value,
		ioc_value: null,
		ioc_type: null,
		ioc_description: null
	}
	return payload
}

function reset() {
	resetForm()
	formRef.value?.restoreValidation()
}

function resetForm() {
	form.value = getForm()
}

function deleteIoc(ioc: AlertIOC) {
	iocsList.value = iocsList.value.filter(o => o.id !== ioc.id)
	emit("deleted", iocsList.value)
}

function submit() {
	submitting.value = true

	Api.incidentManagement
		.createAlertIoc(form.value as AlertIocPayload)
		.then(res => {
			if (res.data.success) {
				iocsList.value.push({
					id: res.data.alert_ioc.ioc_id,
					description: form.value.ioc_description || "",
					type: form.value.ioc_type || "",
					value: form.value.ioc_value || ""
				})
				closeForm(true)
				emit("updated", iocsList.value)
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
