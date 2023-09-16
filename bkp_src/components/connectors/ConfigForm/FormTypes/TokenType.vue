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
import { onMounted, reactive, ref, toRefs } from "vue"
import isURL from "validator/lib/isURL"

export interface ITokenForm {
    connector_url: string
    connector_api_key: string
}

const emit = defineEmits<{
    (e: "mounted", value: FormInstance): void
}>()

const props = defineProps<{
    form: ITokenForm
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
    connector_api_key: [{ required: true, message: "Please input a valid API Key", trigger: "blur" }]
})

onMounted(() => {
    if (formRef.value) {
        emit("mounted", formRef.value)
    }
})
</script>
