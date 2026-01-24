<template>
    <n-form ref="formRef" :model="formValue" :rules="rules" label-placement="top">
        <n-form-item label="Customer" path="customer_code">
            <n-select
                v-model:value="formValue.customer_code"
                :options="customers"
                placeholder="Select customer"
                filterable
                clearable
            />
        </n-form-item>

        <n-form-item label="Report Name (Optional)" path="report_name">
            <n-input
                v-model:value="formValue.report_name"
                placeholder="Leave empty for auto-generated name"
                clearable
            />
        </n-form-item>

        <n-divider>Filters (Optional)</n-divider>

        <n-form-item label="Agent Name" path="agent_name">
            <n-input
                v-model:value="formValue.agent_name"
                placeholder="Filter by specific agent"
                clearable
            />
        </n-form-item>

        <n-form-item label="Policy ID" path="policy_id">
            <n-input
                v-model:value="formValue.policy_id"
                placeholder="Filter by specific policy ID"
                clearable
            />
        </n-form-item>

        <n-form-item label="Minimum Score" path="min_score">
            <n-input-number
                v-model:value="formValue.min_score"
                :min="0"
                :max="100"
                placeholder="Filter by minimum compliance score"
                clearable
                class="w-full"
            />
        </n-form-item>

        <n-form-item label="Maximum Score" path="max_score">
            <n-input-number
                v-model:value="formValue.max_score"
                :min="0"
                :max="100"
                placeholder="Filter by maximum compliance score"
                clearable
                class="w-full"
            />
        </n-form-item>

        <n-space justify="end" class="mt-4">
            <n-button @click="$emit('cancel')">Cancel</n-button>
            <n-button type="primary" :loading="loading" @click="handleGenerate">
                <template #icon>
                    <Icon :name="GenerateIcon" />
                </template>
                Generate Report
            </n-button>
        </n-space>
    </n-form>
</template>

<script setup lang="ts">
import type { FormInst, FormRules } from "naive-ui"
import type { SCAReportGenerateRequest } from "@/types/sca.d"
import { NButton, NDivider, NForm, NFormItem, NInput, NInputNumber, NSelect, NSpace } from "naive-ui"
import { ref } from "vue"
import Icon from "@/components/common/Icon.vue"

const GenerateIcon = "carbon:document-add"

interface Props {
    customers: Array<{ label: string; value: string }>
    loading?: boolean
}

defineProps<Props>()

const emit = defineEmits<{
    generate: [request: SCAReportGenerateRequest]
    cancel: []
}>()

const formRef = ref<FormInst | null>(null)
const formValue = ref<SCAReportGenerateRequest>({
    customer_code: "",
    report_name: undefined,
    agent_name: undefined,
    policy_id: undefined,
    min_score: undefined,
    max_score: undefined
})

const rules: FormRules = {
    customer_code: [
        {
            required: true,
            message: "Please select a customer",
            trigger: ["blur", "change"]
        }
    ]
}

async function handleGenerate() {
    try {
        await formRef.value?.validate()

        // Clean up empty optional fields
        const request: SCAReportGenerateRequest = {
            customer_code: formValue.value.customer_code
        }

        if (formValue.value.report_name) request.report_name = formValue.value.report_name
        if (formValue.value.agent_name) request.agent_name = formValue.value.agent_name
        if (formValue.value.policy_id) request.policy_id = formValue.value.policy_id
        if (formValue.value.min_score !== undefined && formValue.value.min_score !== null) {
            request.min_score = formValue.value.min_score
        }
        if (formValue.value.max_score !== undefined && formValue.value.max_score !== null) {
            request.max_score = formValue.value.max_score
        }

        emit("generate", request)
    } catch (error) {
        console.error("Form validation failed:", error)
    }
}
</script>

<style scoped>
.w-full {
    width: 100%;
}
</style>
