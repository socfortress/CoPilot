<template>
	<n-form ref="formRef" :model="form" :rules="rules">
		<div class="flex flex-col gap-2">
			<n-form-item label="Configuration file" path="file">
				<n-upload v-model:file-list="fileList" :max="1" accept="application/json, .json, .JSON">
					<n-upload-dragger>
						<div>
							<Icon :name="UploadIcon" :size="28" :depth="3" />
						</div>
						<div class="font-semibold">Click or drag a file to this area to upload</div>
						<p class="mt-2">Only .json files are accepted</p>
					</n-upload-dragger>
				</n-upload>
			</n-form-item>
		</div>
	</n-form>
</template>

<script setup lang="ts">
import type { FormInst, FormItemRule, FormRules, UploadFileInfo } from "naive-ui"
import type { ScoutSuiteGcpReportPayload } from "@/types/cloudSecurityAssessment.d"
import { NForm, NFormItem, NUpload, NUploadDragger } from "naive-ui"
import { computed, onMounted, ref, watch } from "vue"
import Icon from "@/components/common/Icon.vue"

const emit = defineEmits<{
	(e: "mounted", value: FormInst): void
	(e: "model", value: Partial<ScoutSuiteGcpReportPayload>): void
	(e: "valid", value: boolean): void
}>()

const form = ref<Partial<ScoutSuiteGcpReportPayload>>({
	file: undefined
})
const formRef = ref<FormInst>()
const UploadIcon = "carbon:document-add"
const fileList = ref<UploadFileInfo[]>([])
const jsonFile = computed<File | null>(() => fileList.value?.[0]?.file || null)
const rules: FormRules = {
	file: {
		required: true,
		validator: validateFile,
		trigger: ["input", "blur"]
	}
}

const isValid = computed(() => {
	if (!form.value.file) return false
	return true
})

function validateFile(rule: FormItemRule, value: File | undefined) {
	if (rule.required && !value) {
		return new Error("Please input the Configuration file")
	}

	return true
}

watch(
	jsonFile,
	val => {
		form.value.file = val || undefined
	},
	{ deep: true, immediate: true }
)

watch(form, val => emit("model", val), { deep: true, immediate: true })

watch(isValid, val => emit("valid", val), { immediate: true })

onMounted(() => {
	if (formRef.value) {
		emit("mounted", formRef.value)
	}
})
</script>
