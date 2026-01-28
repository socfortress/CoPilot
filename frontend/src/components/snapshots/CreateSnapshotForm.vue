<template>
    <n-form ref="formRef" :model="formData" :rules="rules" label-placement="left" label-width="160px">
        <n-form-item label="Snapshot Name" path="snapshot">
            <n-input v-model:value="formData.snapshot" placeholder="Enter snapshot name" />
        </n-form-item>

        <n-form-item label="Indices" path="indices">
            <n-input
                v-model:value="indicesInput"
                placeholder="Enter index patterns (comma-separated, e.g., wazuh_*)"
                type="textarea"
                :rows="2"
            />
        </n-form-item>

        <n-form-item label="Skip Write Indices" path="skip_write_indices">
            <n-switch v-model:value="formData.skip_write_indices" />
            <span class="ml-2 text-sm text-gray-500">Skip indices currently being written to</span>
        </n-form-item>

        <n-form-item label="Include Global State" path="include_global_state">
            <n-switch v-model:value="formData.include_global_state" />
        </n-form-item>

        <n-form-item label="Ignore Unavailable" path="ignore_unavailable">
            <n-switch v-model:value="formData.ignore_unavailable" />
        </n-form-item>

        <n-form-item label="Wait for Completion" path="wait_for_completion">
            <n-switch v-model:value="formData.wait_for_completion" />
            <span class="ml-2 text-sm text-gray-500">Wait for snapshot to complete before returning</span>
        </n-form-item>

        <div class="flex justify-end gap-2 mt-4">
            <n-button @click="$emit('cancel')">Cancel</n-button>
            <n-button type="primary" @click="handleSubmit" :loading="loading">Create Snapshot</n-button>
        </div>
    </n-form>
</template>

<script setup lang="ts">
import { NButton, NForm, NFormItem, NInput, NSwitch, useMessage } from "naive-ui"
import type { FormInst, FormRules } from "naive-ui"
import { computed, ref } from "vue"
import type { CreateSnapshotRequest } from "@/types/snapshots.d"
import Api from "@/api"

const props = defineProps<{
    repository: string | null
}>()

const emit = defineEmits<{
    (e: "success"): void
    (e: "cancel"): void
}>()

const message = useMessage()
const formRef = ref<FormInst | null>(null)
const loading = ref(false)
const indicesInput = ref("")

const formData = ref<Omit<CreateSnapshotRequest, "repository" | "indices">>({
    snapshot: "",
    ignore_unavailable: true,
    include_global_state: false,
    partial: false,
    wait_for_completion: false,
    skip_write_indices: true
})

const rules: FormRules = {
    snapshot: {
        required: true,
        message: "Snapshot name is required",
        trigger: "blur"
    }
}

async function handleSubmit() {
    if (!props.repository) {
        message.error("Repository is required")
        return
    }

    try {
        await formRef.value?.validate()
    } catch {
        return
    }

    loading.value = true
    try {
        const indices = indicesInput.value
            .split(",")
            .map(s => s.trim())
            .filter(s => s.length > 0)

        const request: CreateSnapshotRequest = {
            repository: props.repository,
            snapshot: formData.value.snapshot,
            indices: indices.length > 0 ? indices : undefined,
            ignore_unavailable: formData.value.ignore_unavailable,
            include_global_state: formData.value.include_global_state,
            partial: formData.value.partial,
            wait_for_completion: formData.value.wait_for_completion,
            skip_write_indices: formData.value.skip_write_indices
        }

        const response = await Api.snapshots.createSnapshot(request)
        if (response.data.success) {
            emit("success")
        } else {
            message.error(response.data.message)
        }
    } catch (error: any) {
        message.error(error.message || "Failed to create snapshot")
    } finally {
        loading.value = false
    }
}
</script>
