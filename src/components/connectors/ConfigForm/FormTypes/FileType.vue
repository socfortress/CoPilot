<template>
    <el-form :model="form" status-icon :rules="rules" label-width="120px" ref="formRef" label-position="top">
        <el-form-item label="Connector URL" prop="connector_url">
            <el-input v-model="form.connector_url" required type="url" />
        </el-form-item>
        <el-form-item label="File" prop="file">
            <el-upload class="upload-demo" drag :limit="1" :auto-upload="false" :on-exceed="handleExceed" ref="upload">
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
import { reactive, ref, toRefs } from "vue"

export interface IFileForm {
    connector_url: string
    connector_file: string
}

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
/*
const checkAge = (rule: any, value: any, callback: any) => {
    if (!value) {
        return callback(new Error("Please input the age"))
    }
    setTimeout(() => {
        if (!Number.isInteger(value)) {
            callback(new Error("Please input digits"))
        } else {
            if (value < 18) {
                callback(new Error("Age must be greater than 18"))
            } else {
                callback()
            }
        }
    }, 1000)
}

const validatePass = (rule: any, value: any, callback: any) => {
    if (value === "") {
        callback(new Error("Please input the password"))
    } else {
        if (ruleForm.checkPass !== "") {
            if (!formRef.value) return
            formRef.value.validateField("checkPass", () => null)
        }
        callback()
    }
}
const validatePass2 = (rule: any, value: any, callback: any) => {
    if (value === "") {
        callback(new Error("Please input the password again"))
    } else if (value !== ruleForm.pass) {
        callback(new Error("Two inputs don't match!"))
    } else {
        callback()
    }
}
*/

const rules = reactive<FormRules<typeof form>>({
    connector_url: [{ trigger: "blur" }],
    connector_file: [{ trigger: "blur" }]
})
</script>

<style lang="scss" scoped></style>
