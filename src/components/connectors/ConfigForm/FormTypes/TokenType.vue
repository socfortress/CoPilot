<template>
    <el-form :model="form" status-icon :rules="rules" label-width="120px" ref="formRef" label-position="top">
        <el-form-item label="Connector URL" prop="connector_url">
            <el-input v-model="form.connector_url" required type="url" />
        </el-form-item>
        <el-form-item label="API Key" prop="connector_api_key">
            <el-input v-model="form.connector_api_key" required type="text" />
        </el-form-item>
    </el-form>
</template>

<script setup lang="ts">
import { FormInstance, FormRules } from "element-plus"
import { reactive, ref, toRefs } from "vue"

export interface ITokenForm {
    connector_url: string
    connector_api_key: string
}

const props = defineProps<{
    form: ITokenForm
}>()
const { form } = toRefs(props)

const formRef = ref<FormInstance>()

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
    connector_api_key: [{ trigger: "blur" }]
})
</script>

<style lang="scss" scoped></style>
