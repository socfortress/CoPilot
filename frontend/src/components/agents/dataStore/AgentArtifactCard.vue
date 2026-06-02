<template>
	<CardEntity
		size="small"
		:embedded="!clickable"
		:hoverable
		:clickable
		main-box-class="gap-2!"
		footer-box-class="bg-transparent!"
		@click="emit('click', artifact)"
	>
		<template #headerMain>
			<div class="flex items-center gap-2">
				<Icon :name="FileIcon" :size="16" class="shrink-0 text-primary" />
				<div class="min-w-0">
					<p class="truncate text-sm font-semibold text-primary">{{ artifact.artifact_name }}</p>
					<p class="text-secondary text-xs font-mono">{{ artifact.file_name }}</p>
				</div>
			</div>
		</template>

		<template #headerExtra>
			<n-tag :type="statusType" size="small" round>
				{{ artifact.status }}
			</n-tag>
		</template>

		<template #default>
			<div class="grid grid-cols-1 gap-1 text-xs @lg:grid-cols-2">
				<div class="flex items-center justify-between gap-2">
					<span class="text-secondary uppercase tracking-wide">Flow</span>
					<code class="text-xs font-mono">{{ artifact.flow_id }}</code>
				</div>
				<div class="flex items-center justify-between gap-2">
					<span class="text-secondary uppercase tracking-wide">Size</span>
					<span class="font-mono">{{ fileSize }}</span>
				</div>
				<div class="flex items-center justify-between gap-2">
					<span class="text-secondary uppercase tracking-wide">Collected</span>
					<span class="font-mono">{{ formatDate(artifact.collection_time, dFormats.datetime) }}</span>
				</div>
				<div v-if="artifact.customer_code" class="flex items-center justify-between gap-2">
					<span class="text-secondary uppercase tracking-wide">Customer</span>
					<span class="font-mono">{{ artifact.customer_code }}</span>
				</div>
			</div>
		</template>

		<template v-if="showActions" #footerMain>
			<div class="flex flex-wrap items-center gap-2">
				<n-button size="tiny" secondary type="info" @click.stop="emit('details', artifact)">
					<template #icon>
						<Icon :name="InfoIcon" :size="14" />
					</template>
					Details
				</n-button>
				<n-button size="tiny" secondary type="primary" @click.stop="emit('download', artifact)">
					<template #icon>
						<Icon :name="DownloadIcon" :size="14" />
					</template>
					Download
				</n-button>
				<n-button size="tiny" secondary type="error" @click.stop="emit('delete', artifact)">
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
import type { AgentArtifactData } from "@/types/agents.d"
import bytes from "bytes"
import { NButton, NTag } from "naive-ui"
import { computed } from "vue"
import CardEntity from "@/components/common/cards/CardEntity.vue"
import Icon from "@/components/common/Icon.vue"
import { useSettingsStore } from "@/stores/settings"
import { formatDate } from "@/utils/format"

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

const STATUS_TYPE_MAP: Record<string, TagProps["type"]> = {
	completed: "success",
	failed: "error",
	processing: "warning",
	pending: "info"
} as const

const fileSize = computed(() => bytes(artifact.file_size))
const statusType = computed<TagProps["type"]>(() => STATUS_TYPE_MAP[artifact.status?.toLowerCase()] ?? "default")
</script>
