<template>
    <el-form :model="form" status-icon :rules="rules" label-width="120px" ref="formRef" label-position="top">
        <el-form-item label="Connector URL" prop="connector_url">
            <el-input v-model="form.connector_url" required type="url" />
        </el-form-item>
        <el-form-item label="File" prop="connector_file">
            <el-upload class="file-upload-wrap" drag :limit="1" :auto-upload="false" :on-exceed="handleExceed" ref="upload">
                <el-icon class="el-icon--upload"><upload-filled /></el-icon>
                <div class="el-upload__text">Drop file here or <em>click to upload</em></div>
                <template #tip>
                    <div class="el-upload__tip text-red">limit 1 file, new file will cover the old file</div>
                </template>
            </el-upload>
        </el-form-item>
    </el-form>
</template>

<script setup lang="ts">
import { FormInstance, FormRules } from "element-plus"
import type { UploadInstance, UploadProps, UploadRawFile } from "element-plus"
import { UploadFilled } from "@element-plus/icons-vue"
import { onMounted, reactive, ref, toRefs } from "vue"
import isURL from "validator/lib/isURL"

export interface IFileForm {
    connector_url: string
    connector_file: string
}

const emit = defineEmits<{
    (e: "mounted", value: FormInstance): void
}>()

const props = defineProps<{
    form: IFileForm
}>()
const { form } = toRefs(props)

const formRef = ref<FormInstance>()

const upload = ref<UploadInstance>()

const handleExceed: UploadProps["onExceed"] = files => {
    upload.value!.clearFiles()
    const file = files[0] as UploadRawFile
    upload.value!.handleStart(file)
}

const submitUpload = () => {
    upload.value!.submit()
}

const validateUrl = (rule: any, value: any, callback: any) => {
    if (!value) {
        return callback(new Error("Please input a valid URL"))
    }
    if (!isURL(value)) {
        return callback(new Error("Please input a valid URL"))
    }

    return callback()
}

const rules = reactive<FormRules<typeof form>>({
    connector_url: [{ required: true, validator: validateUrl, trigger: "blur" }],
    connector_file: [{ required: true, message: "Please input a valid File", trigger: "blur" }]
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
