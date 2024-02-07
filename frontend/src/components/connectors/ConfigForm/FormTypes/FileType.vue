<template>
	<n-form :model="form" :rules="rules" label-width="120px" ref="formRef" label-placement="top">
		<n-form-item label="File" path="connector_file">
			<n-upload
				class="file-upload-wrap"
				:max="1"
				:show-file-list="true"
				@change="handleChange"
				@remove="handleChange"
				ref="uploadRef"
				accept=".yaml, .YAML"
			>
				<n-upload-dragger>
					<div>
						<Icon :name="UploadIcon" :size="48" :depth="3"></Icon>
					</div>
					<h4>Click or drag a file to this area to upload</h4>
					<p class="mt-2">Limit 1 file .YAML, new file will cover the old file</p>
				</n-upload-dragger>
			</n-upload>
		</n-form-item>
	</n-form>
</template>

<script setup lang="ts">
import { onMounted, ref, toRefs } from "vue"
import {
	NForm,
	NFormItem,
	NUpload,
	NUploadDragger,
	type FormRules,
	type FormInst,
	type FormItemRule,
	type UploadInst,
	type UploadFileInfo
} from "naive-ui"
import Icon from "@/components/common/Icon.vue"

export interface IFileForm {
	connector_file: File | null
}

const UploadIcon = "carbon:cloud-upload"

const emit = defineEmits<{
	(e: "mounted", value: FormInst): void
}>()

const props = defineProps<{
	form: IFileForm
}>()
const { form } = toRefs(props)

const formRef = ref<FormInst>()
const uploadRef = ref<UploadInst>()

const handleChange = ({ file }: { file: UploadFileInfo }) => {
	if (file.status === "removed") {
		form.value.connector_file = null
	} else {
		form.value.connector_file = file.file || null
	}
	formRef.value?.validate()
}

const validateFile = (rule: FormItemRule, value: File) => {
	if (!value) {
		return new Error("Please input a valid File")
	}

	const stringCheck = value.name + value.type

	if (stringCheck.indexOf("yaml") === -1) {
		return new Error("Please input a valid File")
	}

	return true
}

const rules: FormRules = {
	connector_file: [{ required: true, validator: validateFile, trigger: "blur" }]
}

onMounted(() => {
	if (formRef.value) {
		emit("mounted", formRef.value)
	}
})
</script>
