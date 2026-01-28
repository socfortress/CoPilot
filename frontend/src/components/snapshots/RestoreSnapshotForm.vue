<template>
	<n-form ref="formRef" :model="formData" :rules="rules" label-placement="left" label-width="160px">
		<n-form-item label="Snapshot">
			<n-input :value="snapshot?.snapshot" disabled />
		</n-form-item>

		<n-form-item label="Indices in Snapshot">
			<n-tag v-for="index in snapshot?.indices.slice(0, 5)" :key="index" size="small" class="mr-1 mb-1">
				{{ index }}
			</n-tag>
			<n-tag v-if="(snapshot?.indices.length || 0) > 5" size="small">
				+{{ (snapshot?.indices.length || 0) - 5 }} more
			</n-tag>
		</n-form-item>

		<n-form-item label="Indices to Restore" path="indices">
			<n-input
				v-model:value="indicesInput"
				placeholder="Leave empty to restore all indices, or enter specific indices (comma-separated)"
				type="textarea"
				:rows="2"
			/>
		</n-form-item>

		<n-form-item label="Rename Pattern" path="rename_pattern">
			<n-input v-model:value="formData.rename_pattern" placeholder="e.g., (.+)" />
		</n-form-item>

		<n-form-item label="Rename Replacement" path="rename_replacement">
			<n-input v-model:value="formData.rename_replacement" placeholder="e.g., restored_$1" />
		</n-form-item>

		<n-form-item label="Include Global State" path="include_global_state">
			<n-switch v-model:value="formData.include_global_state" />
		</n-form-item>

		<n-form-item label="Include Aliases" path="include_aliases">
			<n-switch v-model:value="formData.include_aliases" />
		</n-form-item>

		<n-form-item label="Ignore Unavailable" path="ignore_unavailable">
			<n-switch v-model:value="formData.ignore_unavailable" />
		</n-form-item>

		<n-alert type="warning" class="mb-4">
			<strong>Note:</strong> If an index with the same name already exists, use the rename pattern to restore under
			a different name. Example: Pattern <code>(.+)</code> with replacement <code>restored_$1</code>
		</n-alert>

		<div class="flex justify-end gap-2 mt-4">
			<n-button @click="$emit('cancel')">Cancel</n-button>
			<n-button type="primary" :loading="loading" @click="handleSubmit">Restore Snapshot</n-button>
		</div>
	</n-form>
</template>

<script setup lang="ts">
import type { FormInst, FormRules } from "naive-ui"
import type { RestoreSnapshotRequest, SnapshotInfo } from "@/types/snapshots.d"
import { NAlert, NButton, NForm, NFormItem, NInput, NSwitch, NTag, useMessage } from "naive-ui"
import { ref } from "vue"
import Api from "@/api"

const props = defineProps<{
    repository: string | null
    snapshot: SnapshotInfo | null
}>()

const emit = defineEmits<{
    (e: "success"): void
    (e: "cancel"): void
}>()

const message = useMessage()
const formRef = ref<FormInst | null>(null)
const loading = ref(false)
const indicesInput = ref("")

const formData = ref({
    rename_pattern: "(.+)",
    rename_replacement: "restored_$1",
    include_global_state: false,
    include_aliases: true,
    ignore_unavailable: true,
    partial: false
})

const rules: FormRules = {}

async function handleSubmit() {
    if (!props.repository || !props.snapshot) {
        message.error("Repository and snapshot are required")
        return
    }

    loading.value = true
    try {
        const indices = indicesInput.value
            .split(",")
            .map(s => s.trim())
            .filter(s => s.length > 0)

        const request: RestoreSnapshotRequest = {
            repository: props.repository,
            snapshot: props.snapshot.snapshot,
            indices: indices.length > 0 ? indices : undefined,
            rename_pattern: formData.value.rename_pattern || undefined,
            rename_replacement: formData.value.rename_replacement || undefined,
            include_global_state: formData.value.include_global_state,
            include_aliases: formData.value.include_aliases,
            ignore_unavailable: formData.value.ignore_unavailable,
            partial: formData.value.partial
        }

        const response = await Api.snapshots.restoreSnapshot(request)
        if (response.data.success) {
            emit("success")
        } else {
            message.error(response.data.message)
        }
    } catch (error: any) {
        message.error(error.message || "Failed to restore snapshot")
    } finally {
        loading.value = false
    }
}
</script>
