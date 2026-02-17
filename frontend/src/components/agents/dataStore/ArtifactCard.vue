<template>
	<n-card
		class="artifact-card"
		:class="{ 'cursor-pointer': hoverable, clickable }"
		content-style="padding: 16px"
		@click="emit('click', artifact)"
	>
		<div class="flex flex-col gap-3">
			<div class="flex items-start justify-between gap-4">
				<div class="flex grow flex-col gap-1">
					<div class="flex items-center gap-2">
						<Icon :name="FileIcon" :size="18" class="text-primary-color" />
						<span class="text-primary-color font-bold">{{ artifact.artifact_name }}</span>
					</div>
					<div class="text-secondary-color flex items-center gap-2 text-sm">
						<span class="font-mono">{{ artifact.file_name }}</span>
					</div>
				</div>
				<n-badge :value="artifact.status" :type="statusType" />
			</div>

			<n-divider class="my-1!" />

			<div class="flex flex-col gap-2 text-sm">
				<div class="flex items-center justify-between">
					<span class="text-secondary-color">Flow ID:</span>
					<code class="font-mono text-xs">{{ artifact.flow_id }}</code>
				</div>
				<div class="flex items-center justify-between">
					<span class="text-secondary-color">File Size:</span>
					<span>{{ fileSize }}</span>
				</div>
				<div class="flex items-center justify-between">
					<span class="text-secondary-color">Collected:</span>
					<span>{{ formatDate(artifact.collection_time, dFormats.datetime) }}</span>
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
import type { BadgeProps } from "naive-ui"
import type { AgentArtifactData } from "@/types/agents.d"
import bytes from "bytes"
import { NBadge, NButton, NCard, NDivider } from "naive-ui"
import { computed } from "vue"
import Icon from "@/components/common/Icon.vue"
import { useSettingsStore } from "@/stores/settings"
import { formatDate } from "@/utils/format"

// TODO: join ArtifactCard + ArtifactCardCompact

const {
	artifact,
	showActions = false,
	hoverable = false,
	clickable = false
} = defineProps<{
	artifact: AgentArtifactData
	showActions?: boolean
	hoverable?: boolean
	clickable?: boolean
}>()

const emit = defineEmits<{
	(e: "click", artifact: AgentArtifactData): void
	(e: "download", artifact: AgentArtifactData): void
	(e: "delete", artifact: AgentArtifactData): void
	(e: "details", artifact: AgentArtifactData): void
}>()

const dFormats = useSettingsStore().dateFormat

const FileIcon = "lsicon:file-zip-outline"
const DownloadIcon = "carbon:download"
const DeleteIcon = "carbon:trash-can"
const InfoIcon = "carbon:information"

const STATUS_TYPE_MAP: Record<string, BadgeProps["type"]> = {
	completed: "success",
	failed: "error",
	processing: "warning",
	pending: "info"
} as const

const fileSize = computed(() => bytes(artifact.file_size))

const statusType = computed<BadgeProps["type"]>(() => {
	const normalizedStatus = artifact.status.toLowerCase()
	return STATUS_TYPE_MAP[normalizedStatus] ?? "default"
})
</script>

<style lang="scss" scoped>
// TODO: remove style

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
