<template>
	<div class="flex flex-col gap-4">
		<CardEntity size="small" embedded>
			<template #headerMain>
				<div class="flex flex-col gap-0">
					<p class="text-default text-sm font-semibold">{{ artifact.artifact_name }}</p>
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
						<template #value>{{ collectionTime }}</template>
					</Badge>
					<Badge v-if="artifact.customer_code" type="splitted" size="small">
						<template #label>Customer</template>
						<template #value>{{ artifact.customer_code }}</template>
					</Badge>
				</div>
			</template>
		</CardEntity>

		<CardEntity v-for="section in detailSections" :key="section.title" size="small" embedded main-box-class="gap-2">
			<template #headerMain>
				<span class="text-secondary text-xs tracking-wide uppercase">{{ section.title }}</span>
			</template>
			<template #default>
				<div class="grid-auto-fit-200 grid gap-2">
					<CardKV v-for="field in section.fields" :key="field.label">
						<template #key>{{ field.label }}</template>
						<template #value>{{ field.value }}</template>
					</CardKV>
				</div>
			</template>
		</CardEntity>

		<CardEntity v-if="artifact.notes" size="small" embedded>
			<template #headerMain>
				<span class="text-secondary text-xs tracking-wide uppercase">Notes</span>
			</template>
			<template #default>
				<p class="text-default text-sm leading-relaxed whitespace-pre-wrap">{{ artifact.notes }}</p>
			</template>
		</CardEntity>
	</div>
</template>

<script setup lang="ts">
import type { TagProps } from "naive-ui"
import type { AgentArtifactData } from "@/types/agents"
import { NTag } from "naive-ui"
import { computed } from "vue"
import Badge from "@/components/common/Badge.vue"
import CardEntity from "@/components/common/cards/CardEntity.vue"
import CardKV from "@/components/common/cards/CardKV.vue"
import { useSettingsStore } from "@/stores/settings"
import { formatBytes, formatDate } from "@/utils/format"

const { artifact } = defineProps<{ artifact: AgentArtifactData }>()

const dFormats = useSettingsStore().dateFormat

const STATUS_TYPE_MAP: Record<string, TagProps["type"]> = {
	completed: "success",
	failed: "error",
	processing: "warning",
	pending: "info"
} as const

const fileSize = computed(() => formatBytes(artifact.file_size))
const collectionTime = computed(() => formatDate(artifact.collection_time, dFormats.datetime))
const statusType = computed<TagProps["type"]>(() => STATUS_TYPE_MAP[artifact.status?.toLowerCase()] ?? "default")

const detailSections = computed(() => [
	{
		title: "Identifiers",
		fields: [
			{ label: "ID", value: artifact.id },
			{ label: "Agent ID", value: artifact.agent_id },
			{ label: "Velociraptor ID", value: artifact.velociraptor_id },
			{ label: "Flow ID", value: artifact.flow_id }
		]
	},
	{
		title: "File",
		fields: [
			{ label: "File Name", value: artifact.file_name },
			{ label: "File Size", value: fileSize.value },
			{ label: "Content Type", value: artifact.content_type },
			{ label: "File Hash", value: artifact.file_hash }
		]
	},
	{
		title: "Storage",
		fields: [
			{ label: "Bucket", value: artifact.bucket_name },
			{ label: "Object Key", value: artifact.object_key }
		]
	},
	...(artifact.uploaded_by != null
		? [
				{
					title: "Upload",
					fields: [{ label: "Uploaded By", value: artifact.uploaded_by }]
				}
			]
		: [])
])
</script>
