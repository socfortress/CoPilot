<template>
	<el-form :model="form" status-icon :rules="rules" label-width="120px" ref="formRef" label-position="top">
		<el-form-item label="File" prop="connector_file">
			<el-upload
				class="file-upload-wrap"
				drag
				:limit="1"
				:auto-upload="false"
				:on-exceed="handleExceed"
				:on-change="handleChange"
				ref="uploadRef"
				accept=".yaml, .YAML"
			>
				<el-icon class="el-icon--upload"><upload-filled /></el-icon>
				<div class="el-upload__text">
					Drop file here or
					<em>click to upload</em>
				</div>
				<template #tip>
					<div class="el-upload__tip text-red">Limit 1 file .YAML, new file will cover the old file</div>
				</template>
			</el-upload>
		</el-form-item>
	</el-form>
</template>

<script setup lang="ts">
import { FormInstance } from "element-plus"
import type { UploadFile, UploadInstance, UploadProps, UploadRawFile } from "element-plus"
import { UploadFilled } from "@element-plus/icons-vue"
import { onMounted, reactive, ref, toRefs } from "vue"

export interface IFileForm {
	connector_file: File | null
}

const emit = defineEmits<{
	(e: "mounted", value: FormInstance): void
}>()

const props = defineProps<{
	form: IFileForm
}>()
const { form } = toRefs(props)

const formRef = ref<FormInstance>()
const uploadRef = ref<UploadInstance>()

const handleExceed: UploadProps["onExceed"] = (files: File[]) => {
	uploadRef.value!.clearFiles()
	const file = files[0] as UploadRawFile
	uploadRef.value!.handleStart(file)
}

const handleChange: UploadProps["onChange"] = (file: UploadFile) => {
	form.value.connector_file = file.raw
}

const validateFile = (rule: any, value: File, callback: any) => {
	console.log(value)
	if (!value) {
		return callback(new Error("Please input a valid File"))
	}

	if (value.type.indexOf("yaml") === -1) {
		return callback(new Error("Please input a valid File"))
	}

	return callback()
}

const rules = reactive({
	connector_file: [{ required: true, validator: validateFile, trigger: "blur" }]
})

onMounted(() => {
	if (formRef.value) {
		emit("mounted", formRef.value)
	}
})
</script>

<style scoped lang="scss">
.file-upload-wrap {
	width: 100%;

	.el-icon--upload {
		margin-bottom: 0px;
	}

	:deep() {
		.el-upload-dragger {
			padding: 20px 10px;
		}
	}
}
</style>
