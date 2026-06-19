<template>
	<CardEntity size="small" :embedded :hoverable :clickable @click="emit('click', artifact)">
		<template #headerMain>
			<div class="flex flex-col gap-0">
				<p class="text-default truncate text-sm font-semibold">{{ artifact.artifact_name }}</p>
				<p class="text-secondary font-mono text-xs">{{ artifact.file_name }}</p>
			</div>
		</template>

		<template #headerExtra>
			<n-tag :type="statusType" size="small" round>
				{{ artifact.status }}
			</n-tag>
		</template>

		<template #default>
			<div class="flex flex-wrap gap-2">
				<Badge type="splitted" size="small">
					<template #label>Flow</template>
					<template #value>{{ artifact.flow_id }}</template>
				</Badge>
				<Badge type="splitted" size="small">
					<template #label>Size</template>
					<template #value>{{ fileSize }}</template>
				</Badge>
				<Badge type="splitted" size="small">
					<template #label>Collected</template>
					<template #value>{{ formatDate(artifact.collection_time, dFormats.datetime) }}</template>
				</Badge>
				<Badge v-if="artifact.customer_code" type="splitted" size="small">
					<template #label>Customer</template>
					<template #value>{{ artifact.customer_code }}</template>
				</Badge>
			</div>
		</template>

		<template v-if="showActions" #footer>
			<div class="flex flex-wrap items-center justify-end gap-2">
				<n-button size="small" secondary @click.stop="emit('details', artifact)">
					<template #icon>
						<Icon :name="InfoIcon" :size="14" />
					</template>
					Details
				</n-button>
				<n-button size="small" secondary @click.stop="emit('download', artifact)">
					<template #icon>
						<Icon :name="DownloadIcon" :size="14" />
					</template>
					Download
				</n-button>
				<n-button size="small" ghost type="error" @click.stop="emit('delete', artifact)">
					<template #icon>
						<Icon :name="DeleteIcon" :size="14" />
					</template>
					Delete
				</n-button>
			</div>
		</template>
	</CardEntity>
</template>

<script setup lang="ts">
import type { TagProps } from "naive-ui"
import type { AgentArtifactData } from "@/types/agents"
import { NButton, NTag } from "naive-ui"
import { computed } from "vue"
import Badge from "@/components/common/Badge.vue"
import CardEntity from "@/components/common/cards/CardEntity.vue"
import Icon from "@/components/common/Icon.vue"
import { useSettingsStore } from "@/stores/settings"
import { formatBytes, formatDate } from "@/utils/format"

const {
	artifact,
	showActions = true,
	hoverable = true,
	clickable = false,
	embedded = true
} = defineProps<{
	artifact: AgentArtifactData
	showActions?: boolean
	hoverable?: boolean
	clickable?: boolean
	embedded?: boolean
}>()

const emit = defineEmits<{
	(e: "click", artifact: AgentArtifactData): void
	(e: "download", artifact: AgentArtifactData): void
	(e: "delete", artifact: AgentArtifactData): void
	(e: "details", artifact: AgentArtifactData): void
}>()

const dFormats = useSettingsStore().dateFormat

const DownloadIcon = "carbon:download"
const DeleteIcon = "carbon:trash-can"
const InfoIcon = "carbon:information"

const STATUS_TYPE_MAP: Record<string, TagProps["type"]> = {
	completed: "success",
	failed: "error",
	processing: "warning",
	pending: "info"
} as const

const fileSize = computed(() => formatBytes(artifact.file_size))
const statusType = computed<TagProps["type"]>(() => STATUS_TYPE_MAP[artifact.status?.toLowerCase()] ?? "default")
</script>
