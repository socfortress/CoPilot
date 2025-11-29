<template>
	<div class="file-collection-form">
		<n-form ref="formRef" :model="formData" :rules="formRules">
			<n-form-item label="File Path" path="file_path">
				<n-input
					v-model:value="formData.file_path"
					placeholder="e.g., Users\Administrator\Downloads\file.txt or /home/user/file.txt"
					:disabled="loading"
					clearable
				>
					<template #prefix>
						<Icon :name="FileIcon" :size="16" />
					</template>
				</n-input>
			</n-form-item>

			<n-form-item label="Root Disk" path="root_disk">
				<n-input
					v-model:value="formData.root_disk"
					placeholder="e.g., C: (Windows) or / (Linux)"
					:disabled="loading"
					clearable
				>
					<template #prefix>
						<Icon :name="DiskIcon" :size="16" />
					</template>
				</n-input>
			</n-form-item>

			<n-form-item>
				<div class="flex items-center gap-3">
					<n-button
						type="primary"
						:loading="loading"
						:disabled="!formData.file_path || !formData.root_disk"
						@click="handleSubmit"
					>
						<template #icon>
							<Icon :name="CollectIcon" />
						</template>
						Collect File
					</n-button>

					<n-button
						v-if="formData.file_path || formData.root_disk"
						secondary
						:disabled="loading"
						@click="handleReset"
					>
						Reset
					</n-button>
				</div>
			</n-form-item>
		</n-form>

		<n-divider v-if="result" class="my-4!" />

		<n-alert
			v-if="result"
			:type="result.success ? 'success' : 'error'"
			:title="result.success ? 'Collection Started' : 'Collection Failed'"
			closable
			@close="result = null"
		>
			<template v-if="result.success">
				<div class="flex flex-col gap-2">
					<div v-if="result.flow_id">
						<strong>Flow ID:</strong>
						<code class="ml-2">{{ result.flow_id }}</code>
					</div>
					<div v-if="result.session_id">
						<strong>Session ID:</strong>
						<code class="ml-2">{{ result.session_id }}</code>
					</div>
					<div class="text-sm text-secondary-color mt-2">
						{{ result.message }}
					</div>
				</div>
			</template>
			<template v-else>
				{{ result.message }}
			</template>
		</n-alert>
	</div>
</template>

<script setup lang="ts">
import type { FormInst, FormRules } from "naive-ui"
import type { FileCollectionResult } from "@/types/artifacts.d"
import { NAlert, NButton, NDivider, NForm, NFormItem, NInput, useMessage } from "naive-ui"
import { ref } from "vue"
import Api from "@/api"
import Icon from "@/components/common/Icon.vue"

const props = defineProps<{
    agentId: string
}>()

const emit = defineEmits<{
    (e: "success", result: FileCollectionResult): void
    (e: "error", error: string): void
}>()

const FileIcon = "carbon:document"
const DiskIcon = "carbon:storage-pool"
const CollectIcon = "carbon:download"

const message = useMessage()
const formRef = ref<FormInst | null>(null)
const loading = ref(false)

const formData = ref({
    file_path: "",
    root_disk: ""
})

const result = ref<FileCollectionResult | null>(null)

const formRules: FormRules = {
    file_path: [
        {
            required: true,
            message: "File path is required",
            trigger: ["blur", "input"]
        }
    ],
    root_disk: [
        {
            required: true,
            message: "Root disk is required",
            trigger: ["blur", "input"]
        }
    ]
}

async function handleSubmit() {
    if (!formRef.value) return

    try {
        await formRef.value.validate()
    } catch {
       message.warning("You must fill in the required fields correctly.")
			return false
    }

    loading.value = true
    result.value = null

    Api.artifacts
        .collectFileByAgentId(props.agentId, {
            file: formData.value.file_path,
            root_disk: formData.value.root_disk
        })
        .then(res => {
            if (res.data.success) {
                result.value = {
                    success: true,
                    message: res.data.message || "File collection started successfully",
                    flow_id: res.data.flow_id,
                    session_id: res.data.session_id
                }
                message.success("File collection started successfully")
                emit("success", result.value)
            } else {
                result.value = {
                    success: false,
                    message: res.data?.message || "Failed to start file collection"
                }
                message.error(result.value.message)
                emit("error", result.value.message)
            }
        })
        .catch(err => {
            const errorMessage = err.response?.data?.message || "An error occurred during file collection"
            result.value = {
                success: false,
                message: errorMessage
            }
            message.error(errorMessage)
            emit("error", errorMessage)
        })
        .finally(() => {
            loading.value = false
        })
}

function handleReset() {
    formData.value = {
        file_path: "",
        root_disk: ""
    }
    result.value = null
    formRef.value?.restoreValidation()
}

// Expose methods for parent components
defineExpose({
    reset: handleReset
})
</script>

<style lang="scss" scoped>
// TODO: remove style

.file-collection-form {
    max-width: 600px;

    :deep(.n-form-item) {
        margin-bottom: 20px;
    }

    code {
        font-family: var(--font-family-mono);
        font-size: 12px;
        padding: 2px 6px;
        background-color: var(--bg-secondary-color);
        border-radius: 3px;
    }
}
</style>
