<template>
    <el-form :model="form" status-icon :rules="rules" label-width="120px" ref="formRef" label-position="top">
        <el-form-item label="Connector URL" prop="connector_url">
            <el-input v-model="form.connector_url" required type="url" />
        </el-form-item>
        <el-form-item label="Username" prop="connector_username">
            <el-input v-model="form.connector_username" required type="text" />
        </el-form-item>
        <el-form-item label="Password" prop="connector_password">
            <el-input v-model="form.connector_password" required type="password" />
        </el-form-item>
    </el-form>
</template>

<script setup lang="ts">
import { FormInstance, FormRules } from "element-plus"
import { reactive, ref, toRefs } from "vue"

export interface ICredentialsForm {
    connector_url: string
    connector_username: string
    connector_password: string
}

const props = defineProps<{
    form: ICredentialsForm
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
    connector_username: [{ trigger: "blur" }],
    connector_password: [{ trigger: "blur" }]
})
</script>

<style lang="scss" scoped></style>
