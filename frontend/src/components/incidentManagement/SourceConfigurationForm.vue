<template>
	<n-spin :show="loading" class="creation-report-form">
		<n-form :model="form" :rules="rules" ref="formRef">
			<div class="flex flex-col gap-8">
				<div class="flex flex-col gap-2">
					<n-form-item label="Index name" path="index_name" v-if="showIndexNameField">
						<n-select
							v-model:value="form.index_name"
							:options="indexNamesOptions"
							placeholder="Select..."
							clearable
							filterable
							to="body"
							:disabled="disableIndexNameField"
							:loading="loadingIndexNames"
						/>
					</n-form-item>
					<n-form-item label="Source" path="source" v-if="showSourceField">
						<n-input
							v-model:value.trim="form.source"
							placeholder="Please insert Source"
							clearable
							@update:value="resetIndexAvailable()"
							:disabled="disableSourceField"
							:loading="loadingSource"
						/>
					</n-form-item>

					<n-alert v-if="isSourceNotAllowed" title="Source already exists" type="warning" class="mb-5">
						A configuration for
						<strong>"{{ form.source }}"</strong>
						already exists. Please select a different
						<strong>Index name</strong>
						to proceed.
					</n-alert>

					<n-form-item label="Field names" path="field_names">
						<n-select
							v-model:value="form.field_names"
							:options="availableMappingsOptions"
							placeholder="Select..."
							clearable
							filterable
							multiple
							to="body"
							:disabled="!isFieldEnabled"
							:loading="loadingAvailableMappings"
						/>
					</n-form-item>
					<n-form-item label="Asset name" path="asset_name">
						<n-select
							v-model:value="form.asset_name"
							:options="availableMappingsOptions"
							placeholder="Select..."
							clearable
							filterable
							to="body"
							:disabled="!isFieldEnabled"
							:loading="loadingAvailableMappings"
						/>
					</n-form-item>
					<n-form-item label="Timefield name" path="timefield_name">
						<n-select
							v-model:value="form.timefield_name"
							:options="availableMappingsOptions"
							placeholder="Select..."
							clearable
							filterable
							to="body"
							:disabled="!isFieldEnabled"
							:loading="loadingAvailableMappings"
						/>
					</n-form-item>
					<n-form-item label="Alert title name" path="alert_title_name">
						<n-select
							v-model:value="form.alert_title_name"
							:options="availableMappingsOptions"
							placeholder="Select..."
							clearable
							filterable
							to="body"
							:disabled="!isFieldEnabled"
							:loading="loadingAvailableMappings"
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
	NForm,
	NFormItem,
	NInput,
	NButton,
	NSpin,
	NSelect,
	NAlert,
	useMessage,
	type FormValidationError,
	type FormInst,
	type FormRules,
	type MessageReactive,
	type FormItemRule
} from "naive-ui"
import type { SourceConfiguration, SourceName, SourceConfigurationModel } from "@/types/incidentManagement.d"
import _intersection from "lodash/intersection"

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
	sourceConfigurationModel?: SourceConfigurationModel
	showSourceField?: boolean
	disableSourceField?: boolean
	showIndexNameField?: boolean
	disableIndexNameField?: boolean
	disabledSources?: SourceName[]
}>()
const {
	sourceConfigurationModel,
	showSourceField,
	disableSourceField,
	showIndexNameField,
	disableIndexNameField,
	disabledSources
} = toRefs(props)

const submitting = ref(false)
const loadingSource = ref(false)
const loadingIndexNames = ref(false)
const loadingAvailableMappings = ref(false)
const loading = computed(() => loadingAvailableMappings.value || loadingIndexNames.value || loadingSource.value)
const message = useMessage()
const form = ref<SourceConfigurationModel>(getSourceConfigurationForm())
const formRef = ref<FormInst | null>(null)
const availableMappingsOptions = ref<{ label: string; value: string }[]>([])
const indexNamesOptions = ref<{ label: string; value: string }[]>([])

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

const isSourceNotAllowed = computed(
	() => form.value.source && disabledSources.value?.length && disabledSources.value.includes(form.value.source)
)
const isFieldEnabled = computed(() => form.value.index_name && !isSourceNotAllowed.value)

const isValid = computed(() => {
	if (
		!form.value.field_names.length ||
		!form.value.asset_name ||
		!form.value.timefield_name ||
		!form.value.alert_title_name ||
		!form.value.source ||
		isSourceNotAllowed.value
	) {
		return false
	}

	return true
})

watch(sourceConfigurationModel, () => {
	reset()
	init()
})

watch(
	() => form.value.index_name,
	val => {
		if (val) {
			getAvailableMappings(val)
			getSourceByIndex(val)
		} else {
			availableMappingsOptions.value = []
		}
	}
)

function resetIndexAvailable() {
	form.value.index_name = null
	if (form.value.source) {
		getAvailableIndices(form.value.source)
	}
}

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

function getSourceConfigurationForm(): SourceConfigurationModel {
	return {
		field_names: sourceConfigurationModel.value?.field_names || [],
		asset_name: sourceConfigurationModel.value?.asset_name || null,
		timefield_name: sourceConfigurationModel.value?.timefield_name || null,
		alert_title_name: sourceConfigurationModel.value?.alert_title_name || null,
		source: sourceConfigurationModel.value?.source || "",
		index_name: sourceConfigurationModel.value?.index_name || null
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

function sanitizeFields() {
	const availableMappings = availableMappingsOptions.value.map(o => o.value)

	form.value.field_names = _intersection(availableMappings, form.value.field_names)

	if (form.value.asset_name && !availableMappings.includes(form.value.asset_name)) {
		form.value.asset_name = null
	}
	if (form.value.timefield_name && !availableMappings.includes(form.value.timefield_name)) {
		form.value.timefield_name = null
	}
	if (form.value.alert_title_name && !availableMappings.includes(form.value.alert_title_name)) {
		form.value.alert_title_name = null
	}
}

function submit() {
	const payload: SourceConfiguration = {
		field_names: form.value?.field_names || [],
		asset_name: form.value?.asset_name || "",
		timefield_name: form.value?.timefield_name || "",
		alert_title_name: form.value?.alert_title_name || "",
		source: form.value?.source || ""
	}
	emit("submitted", payload)
}

function toggleSubmittingFlag(status?: boolean) {
	if (status !== undefined) {
		submitting.value = status
	} else {
		submitting.value = !submitting.value
	}

	return submitting.value
}

function resetSource() {
	form.value.source = ""
}

function getAvailableMappings(indexName: string) {
	loadingAvailableMappings.value = true

	Api.incidentManagement
		.getAvailableMappings(indexName)
		.then(res => {
			if (res.data.success) {
				availableMappingsOptions.value = (res.data?.available_mappings || []).map(o => ({
					label: o,
					value: o
				}))
				sanitizeFields()
			} else {
				message.warning(res.data?.message || "An error occurred. Please try again later.")
			}
		})
		.catch(err => {
			message.error(err.response?.data?.message || "An error occurred. Please try again later.")
		})
		.finally(() => {
			loadingAvailableMappings.value = false
		})
}

function getAvailableIndices(source: SourceName) {
	loadingIndexNames.value = true

	Api.incidentManagement
		.getAvailableIndices(source)
		.then(res => {
			if (res.data.success) {
				indexNamesOptions.value = (res.data?.indices || []).map(o => ({
					label: o,
					value: o
				}))
			} else {
				resetSource()
				message.warning(res.data?.message || "An error occurred. Please try again later.")
			}
		})
		.catch(err => {
			resetSource()
			message.error(err.response?.data?.message || "An error occurred. Please try again later.")
		})
		.finally(() => {
			loadingIndexNames.value = false
		})
}

function getSourceByIndex(indexName: string) {
	loadingSource.value = true

	Api.incidentManagement
		.getSourceByIndex(indexName)
		.then(res => {
			if (res.data.success) {
				form.value.source = res.data.source
			} else {
				resetSource()
				message.warning(res.data?.message || "An error occurred. Please try again later.")
			}
		})
		.catch(err => {
			resetSource()
			message.error(err.response?.data?.message || "An error occurred. Please try again later.")
		})
		.finally(() => {
			loadingSource.value = false
		})
}

function init() {
	if (sourceConfigurationModel.value?.index_name) {
		getAvailableMappings(sourceConfigurationModel.value.index_name)

		if (!sourceConfigurationModel.value?.source) {
			getSourceByIndex(sourceConfigurationModel.value.index_name)
		}
	}
	if (sourceConfigurationModel.value?.source) {
		getAvailableIndices(sourceConfigurationModel.value.source)
	}
}

onBeforeMount(() => {
	init()
})

onMounted(() => {
	emit("mounted", {
		reset,
		toggleSubmittingFlag
	})
})
</script>
