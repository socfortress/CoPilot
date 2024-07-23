<template>
	<n-spin :show="loading" class="creation-report-form">
		<n-form :model="form" :rules="rules" ref="formRef">
			<div class="flex flex-col gap-8">
				<div class="flex flex-col gap-2">
					<n-form-item label="Source" path="source" v-if="showSourceField">
						<n-input
							v-model:value.trim="form.source"
							placeholder="Please insert Source"
							clearable
							:disabled="disableSourceField"
						/>
					</n-form-item>
					<n-form-item label="Field names" path="field_names">
						<n-select
							v-model:value="form.field_names"
							:options="fieldNamesOptions"
							placeholder="Select..."
							clearable
							multiple
							to="body"
							:loading="loadingFieldNames"
						/>
					</n-form-item>
					<n-form-item label="Asset name" path="asset_name">
						<n-input
							v-model:value.trim="form.asset_name"
							placeholder="Please insert Asset name"
							clearable
						/>
					</n-form-item>
					<n-form-item label="Timefield name" path="timefield_name">
						<n-input
							v-model:value.trim="form.timefield_name"
							placeholder="Please insert Timefield name"
							clearable
						/>
					</n-form-item>
					<n-form-item label="Alert title name" path="alert_title_name">
						<n-input
							v-model:value.trim="form.alert_title_name"
							placeholder="Please insert Alert title name"
							clearable
						/>
					</n-form-item>
				</div>
				<div class="flex justify-between gap-3">
					<div>
						<slot name="additionalActions"></slot>
					</div>
					<div class="flex gap-3 items-center">
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
			</div>
		</n-form>
	</n-spin>
</template>

<script setup lang="ts">
import { computed, onBeforeMount, onMounted, ref, toRefs, watch } from "vue"
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
	type MessageReactive,
	type FormItemRule
} from "naive-ui"
import type { SourceConfiguration, SourceName } from "@/types/incidentManagement.d"
import type { SourceConfigurationPayload } from "@/api/endpoints/incidentManagement"

const emit = defineEmits<{
	(e: "submitted", value: SourceConfiguration): void
	(
		e: "mounted",
		value: {
			reset: () => void
			toggleSubmittingFlag: () => boolean
		}
	): void
}>()

const props = defineProps<{
	sourceConfiguration?: SourceConfiguration
	showSourceField?: boolean
	disableSourceField?: boolean
}>()
const { sourceConfiguration } = toRefs(props)

const submitting = ref(false)
const loadingFieldNames = ref(false)
const loading = computed(() => loadingFieldNames.value)
const message = useMessage()
const form = ref<SourceConfigurationPayload>(getSourceConfigurationForm())
const formRef = ref<FormInst | null>(null)
const fieldNamesOptions = ref<{ label: string; value: string }[]>([])

const rules: FormRules = {
	source: {
		required: true,
		message: "Please input the Source",
		trigger: ["input", "blur"]
	},
	field_names: {
		required: true,
		validator: validateAtLeastOne,
		trigger: ["blur"]
	},
	asset_name: {
		required: true,
		message: "Please input the asset name",
		trigger: ["input", "blur"]
	},
	timefield_name: {
		required: true,
		message: "Please input the timefield name",
		trigger: ["input", "blur"]
	},
	alert_title_name: {
		required: true,
		message: "Please input the alert title name",
		trigger: ["input", "blur"]
	}
}

let validationMessage: MessageReactive | null = null

const isValid = computed(() => {
	if (
		!form.value.field_names.length ||
		!form.value.asset_name ||
		!form.value.timefield_name ||
		!form.value.alert_title_name
	) {
		return false
	}

	return true
})

watch(sourceConfiguration, () => {
	reset()
})

watch(
	() => form.value.source,
	val => {
		if (val) {
			form.value.field_names = []
			getAvailableMappings(val)
		} else {
			fieldNamesOptions.value = []
		}
	}
)

function validateAtLeastOne(rule: FormItemRule, value: string[]) {
	if (!value || !value.length) {
		return new Error("Please select at least one option")
	}

	return true
}

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

function getSourceConfigurationForm(): SourceConfigurationPayload {
	return {
		field_names: sourceConfiguration.value?.field_names || [],
		asset_name: sourceConfiguration.value?.asset_name || "",
		timefield_name: sourceConfiguration.value?.timefield_name || "",
		alert_title_name: sourceConfiguration.value?.alert_title_name || "",
		source: sourceConfiguration.value?.source || ""
	}
}

function reset() {
	if (!loading.value) {
		resetForm()
		formRef.value?.restoreValidation()
	}
}

function resetForm() {
	form.value = getSourceConfigurationForm()
}

function submit() {
	emit("submitted", form.value)
}

function toggleSubmittingFlag(status?: boolean) {
	if (status !== undefined) {
		submitting.value = status
	} else {
		submitting.value = !submitting.value
	}

	return submitting.value
}

function getAvailableMappings(sourceName?: SourceName) {
	loadingFieldNames.value = true

	Api.incidentManagement
		.getAvailableMappings(sourceName || sourceConfiguration.value?.source || "")
		.then(res => {
			if (res.data.success) {
				fieldNamesOptions.value = (res.data?.available_mappings || []).map(o => ({
					label: o,
					value: o
				}))
			} else {
				message.warning(res.data?.message || "An error occurred. Please try again later.")
			}
		})
		.catch(err => {
			message.error(err.response?.data?.message || "An error occurred. Please try again later.")
		})
		.finally(() => {
			loadingFieldNames.value = false
		})
}

onBeforeMount(() => {
	getAvailableMappings()
})

onMounted(() => {
	emit("mounted", {
		reset,
		toggleSubmittingFlag
	})
})
</script>
