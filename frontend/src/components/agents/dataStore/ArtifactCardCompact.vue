<template>
	<n-card size="small" :bordered="true" hoverable class="artifact-card-compact">
		<div class="flex items-start justify-between gap-3">
			<div class="flex-1 min-w-0">
				<div class="flex items-center gap-2 mb-1">
					<Icon :name="FileIcon" :size="16" class="text-primary-color shrink-0" />
					<span class="font-semibold text-sm truncate">{{ artifact.artifact_name }}</span>
					<n-tag :type="getStatusType(artifact.status)" size="small" round>
						{{ artifact.status }}
					</n-tag>
				</div>
				<div class="text-xs text-secondary-color mb-2">
					<code class="text-xs">{{ artifact.file_name }}</code>
				</div>
				<div class="flex flex-wrap gap-x-3 gap-y-1 text-xs text-secondary-color">
					<span>Size: {{ fileSize }}</span>
					<span>{{ formatDate(artifact.collection_time, dFormats.datetime) }}</span>
				</div>
			</div>

			<div v-if="showActions" class="flex flex-col gap-1 shrink-0">
				<n-button size="tiny" secondary type="info" @click.stop="emit('details', artifact)">
					<template #icon>
						<Icon :name="InfoIcon" :size="14" />
					</template>
				</n-button>
				<n-button size="tiny" secondary type="primary" @click.stop="emit('download', artifact)">
					<template #icon>
						<Icon :name="DownloadIcon" :size="14" />
					</template>
				</n-button>
				<n-button size="tiny" secondary type="error" @click.stop="emit('delete', artifact)">
					<template #icon>
						<Icon :name="DeleteIcon" :size="14" />
					</template>
				</n-button>
			</div>
		</div>
	</n-card>
</template>

<script setup lang="ts">
import type { AgentArtifactData } from "@/types/agents.d"
import bytes from "bytes"
import { NButton, NCard, NTag } from "naive-ui"
import { computed } from "vue"
import Icon from "@/components/common/Icon.vue"
import { useSettingsStore } from "@/stores/settings"
import { formatDate } from "@/utils"

const { artifact, showActions = false } = defineProps<{
    artifact: AgentArtifactData
    showActions?: boolean
}>()

const emit = defineEmits<{
    (e: "download", artifact: AgentArtifactData): void
    (e: "delete", artifact: AgentArtifactData): void
    (e: "details", artifact: AgentArtifactData): void
}>()

const dFormats = useSettingsStore().dateFormat

const FileIcon = "lsicon:file-zip-outline"
const DownloadIcon = "carbon:download"
const DeleteIcon = "carbon:trash-can"
	const InfoIcon = "carbon:information"

const fileSize = computed(() => bytes(artifact.file_size))

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
</script>

<style lang="scss" scoped>
// TODO: remove style

.artifact-card-compact {
    transition: all 0.2s var(--bezier-ease);

    &:hover {
        border-color: var(--primary-color);
    }
}
</style>
