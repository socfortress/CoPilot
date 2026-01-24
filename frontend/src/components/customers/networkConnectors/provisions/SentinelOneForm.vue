<template>
    <n-form :model="model" label-placement="left" label-width="auto">
        <n-form-item label="Protocol" required>
            <n-radio-group v-model:value="model.protocol">
                <n-radio-button value="tcp">TCP</n-radio-button>
            </n-radio-group>
        </n-form-item>

        <n-form-item label="Hot Data Retention (days)" required>
            <n-input-number v-model:value="model.hot_data_retention" :min="1" :max="90" class="w-full" />
        </n-form-item>

        <n-form-item label="Index Replicas" required>
            <n-input-number v-model:value="model.index_replicas" :min="0" :max="3" class="w-full" />
        </n-form-item>
    </n-form>
</template>

<script setup lang="ts">
import { NForm, NFormItem, NInputNumber, NRadioButton, NRadioGroup } from "naive-ui"

export interface SentinelOneModel {
    protocol: "tcp"
    hot_data_retention: number
    index_replicas: number
}

const model = defineModel<SentinelOneModel>("options", { required: true })
</script>
