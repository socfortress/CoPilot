<template>
    <n-card
        class="artifact-card"
        :class="{ 'cursor-pointer': hoverable, clickable }"
        content-style="padding: 16px"
        @click="handleClick"
    >
        <div class="flex flex-col gap-3">
            <div class="flex items-start justify-between gap-4">
                <div class="flex flex-col gap-1 grow">
                    <div class="flex items-center gap-2">
                        <Icon :name="FileIcon" :size="18" class="text-primary-color" />
                        <span class="font-bold text-primary-color">{{ artifact.artifact_name }}</span>
                    </div>
                    <div class="flex items-center gap-2 text-sm text-secondary-color">
                        <span class="font-mono">{{ artifact.file_name }}</span>
                    </div>
                </div>
                <n-badge :value="artifact.status" :type="getStatusType(artifact.status)" />
            </div>

            <n-divider class="!my-1" />

            <div class="flex flex-col gap-2 text-sm">
                <div class="flex items-center justify-between">
                    <span class="text-secondary-color">Flow ID:</span>
                    <code class="font-mono text-xs">{{ artifact.flow_id }}</code>
                </div>
                <div class="flex items-center justify-between">
                    <span class="text-secondary-color">File Size:</span>
                    <span>{{ formatFileSize(artifact.file_size) }}</span>
                </div>
                <div class="flex items-center justify-between">
                    <span class="text-secondary-color">Collected:</span>
                    <span>{{ formatDate(artifact.collection_time) }}</span>
                </div>
                <div v-if="artifact.customer_code" class="flex items-center justify-between">
                    <span class="text-secondary-color">Customer:</span>
                    <span>{{ artifact.customer_code }}</span>
                </div>
            </div>

            <div v-if="showActions" class="flex gap-2">
                <n-button size="small" secondary type="info" @click.stop="emit('details', artifact)">
                    <template #icon>
                        <Icon :name="InfoIcon" />
                    </template>
                    Details
                </n-button>
                <n-button size="small" secondary type="primary" @click.stop="emit('download', artifact)">
                    <template #icon>
                        <Icon :name="DownloadIcon" />
                    </template>
                    Download
                </n-button>
                <n-button size="small" secondary type="error" @click.stop="emit('delete', artifact)">
                    <template #icon>
                        <Icon :name="DeleteIcon" />
                    </template>
                    Delete
                </n-button>
            </div>
        </div>
    </n-card>
</template>

<script setup lang="ts">
import type { AgentArtifactData } from "@/types/agents.d"
import { NBadge, NButton, NCard, NDivider } from "naive-ui"
import Icon from "@/components/common/Icon.vue"
import { formatDate } from "@/utils"

interface Props {
    artifact: AgentArtifactData
    showActions?: boolean
    hoverable?: boolean
    clickable?: boolean
}

withDefaults(defineProps<Props>(), {
    showActions: false,
    hoverable: false,
    clickable: false
})

const emit = defineEmits<{
    (e: "click", artifact: AgentArtifactData): void
    (e: "download", artifact: AgentArtifactData): void
    (e: "delete", artifact: AgentArtifactData): void
    (e: "details", artifact: AgentArtifactData): void
}>()

const FileIcon = "carbon:document-zip"
const DownloadIcon = "carbon:download"
const DeleteIcon = "carbon:trash-can"
const InfoIcon = "carbon:information"

function handleClick() {
    emit("click", props.artifact)
}

function getStatusType(status: string) {
    switch (status.toLowerCase()) {
        case "completed":
            return "success"
        case "failed":
            return "error"
        case "processing":
            return "warning"
        default:
            return "default"
    }
}

function formatFileSize(bytes: number): string {
    if (bytes === 0) return "0 Bytes"
    const k = 1024
    const sizes = ["Bytes", "KB", "MB", "GB"]
    const i = Math.floor(Math.log(bytes) / Math.log(k))
    return Math.round((bytes / Math.pow(k, i)) * 100) / 100 + " " + sizes[i]
}
</script>

<style lang="scss" scoped>
.artifact-card {
    border-radius: var(--border-radius);
    overflow: hidden;
    transition: all 0.2s var(--bezier-ease);

    &.hoverable {
        &:hover {
            box-shadow: 0 0 0 1px var(--primary-color);
        }
    }

    &.clickable {
        cursor: pointer;
    }
}
</style>
