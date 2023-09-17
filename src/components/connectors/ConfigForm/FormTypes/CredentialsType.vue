<template>
    <el-form :model="form" status-icon :rules="rules" label-width="120px" ref="formRef" label-position="top">
        <el-form-item label="Connector URL" prop="connector_url">
            <el-input v-model="form.connector_url" required type="url" />
        </el-form-item>
        <el-form-item label="Username" prop="connector_username">
            <el-input v-model="form.connector_username" required type="text" />
        </el-form-item>
        <el-form-item label="Password" prop="connector_password">
            <el-input v-model="form.connector_password" required type="password" autocomplete="off" />
        </el-form-item>
    </el-form>
</template>

<script setup lang="ts">
import { FormInstance, FormRules } from "element-plus"
import { onMounted, reactive, ref, toRefs } from "vue"
import isURL from "validator/lib/isURL"

export interface ICredentialsForm {
    connector_url: string
    connector_username: string
    connector_password: string
}

const emit = defineEmits<{
    (e: "mounted", value: FormInstance): void
}>()

const props = defineProps<{
    form: ICredentialsForm
}>()
const { form } = toRefs(props)

const formRef = ref<FormInstance>()

const validateUrl = (rule: any, value: string, callback: any) => {
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
    connector_username: [{ required: true, message: "Please input a valid Username", trigger: "blur" }],
    connector_password: [{ required: true, message: "Please input a valid Password", trigger: "blur" }]
})

onMounted(() => {
    if (formRef.value) {
        emit("mounted", formRef.value)
    }
})
</script>
