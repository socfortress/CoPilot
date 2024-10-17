<template>
	<n-button :size type="primary" :loading="exporting" secondary @click="showForm = true">
		<template #icon>
			<Icon :name="ReportIcon" />
		</template>
		Generate Report
	</n-button>

	<n-modal
		v-model:show="showForm"
		display-directive="show"
		preset="card"
		:style="{ maxWidth: 'min(600px, 90vw)', minHeight: 'min(270px, 90vh)', overflow: 'hidden' }"
		title="Generate Report"
		:bordered="false"
		segmented
	>
		<n-spin :show="exporting" class="creation-report-form">
			<n-form ref="formRef" :model="form" :rules="rules">
				<div class="flex flex-col gap-2">
					<n-form-item label="Template" path="template_name">
						<CaseReportTemplateSelect v-model:value="form.template_name" />
					</n-form-item>
					<n-form-item label="Filename" path="file_name">
						<n-input-group>
							<n-input
								v-model:value.trim="form.file_name"
								placeholder="Please insert File Name"
								clearable
							/>
							<n-input-group-label>.docx</n-input-group-label>
						</n-input-group>
					</n-form-item>

					<div class="mt-8 flex justify-between gap-4">
						<n-button :disabled="exporting" @click="reset()">Reset</n-button>
						<n-button
							type="primary"
							:disabled="!isValid"
							:loading="exporting"
							@click="validate(() => exportCases())"
						>
							Generate
						</n-button>
					</div>
				</div>
			</n-form>
		</n-spin>
	</n-modal>
</template>

<script setup lang="ts">
import type { CaseReportPayload } from "@/api/endpoints/incidentManagement"
import type { DeepNullable } from "@/types/common"
import type { Size } from "naive-ui/es/button/src/interface"
import Api from "@/api"
import Icon from "@/components/common/Icon.vue"
import { useSettingsStore } from "@/stores/settings"
import { formatDate } from "@/utils"
import { saveAs } from "file-saver"
import {
	type FormInst,
	type FormRules,
	type FormValidationError,
	NButton,
	NForm,
	NFormItem,
	NInput,
	NInputGroup,
	NInputGroupLabel,
	NModal,
	NSpin,
	useMessage
} from "naive-ui"
import { computed, ref } from "vue"
import CaseReportTemplateSelect from "./CaseReportTemplateSelect.vue"

const { size, caseId } = defineProps<{ size?: Size; caseId: number }>()

const ReportIcon = "carbon:report-data"
const dFormats = useSettingsStore().dateFormat
const exporting = ref(false)
const showForm = ref(false)
const message = useMessage()
const form = ref<DeepNullable<CaseReportPayload>>(getClearForm())
const formRef = ref<FormInst | null>(null)

const rules: FormRules = {
	template_name: {
		required: true,
		message: "Please input the Report Template",
		trigger: ["input", "blur"]
	},
	file_name: {
		required: true,
		message: "Please input the Report Filename",
		trigger: ["input", "blur"]
	}
}

const isValid = computed(() => {
	if (!form.value.template_name) {
		return false
	}
	if (!form.value.file_name) {
		return false
	}

	return true
})

function validate(cb?: () => void) {
	if (!formRef.value) return

	formRef.value.validate((errors?: Array<FormValidationError>) => {
		if (!errors) {
			if (cb) cb()
		} else {
			message.warning("You must fill in the required fields correctly.")
			return false
		}
	})
}

function getClearForm(): DeepNullable<CaseReportPayload> {
	return {
		case_id: caseId,
		file_name: null,
		template_name: null
	}
}

function reset(force?: boolean) {
	if (!exporting.value || force) {
		resetForm()
		formRef.value?.restoreValidation()
	}
}

function resetForm() {
	form.value = getClearForm()
}

function exportCases() {
	if (!form.value.file_name || !form.value.template_name) return

	exporting.value = true

	const fileName = form.value.file_name
		? `${form.value.file_name}.docx`
		: `case:${caseId}_report_${formatDate(new Date(), dFormats.datetimesec)}.docx`

	Api.incidentManagement
		.generateCaseReport({
			case_id: caseId,
			file_name: form.value.file_name,
			template_name: form.value.template_name
		})
		.then(res => {
			if (res.data) {
				saveAs(
					new Blob([res.data], {
						type: "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
					}),
					fileName
				)
				reset(true)
			} else {
				message.warning("An error occurred. Please try again later.")
			}
		})
		.catch(err => {
			message.error(err.response?.data?.message || "An error occurred. Please try again later.")
		})
		.finally(() => {
			exporting.value = false
		})
}
</script>
