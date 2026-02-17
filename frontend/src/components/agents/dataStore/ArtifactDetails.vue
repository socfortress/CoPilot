<template>
	<div class="artifact-details flex flex-col gap-4">
		<n-descriptions :column="1" bordered size="small">
			<n-descriptions-item v-for="field in visibleFields" :key="field.key" :label="field.label">
				<component :is="field.component" v-bind="field.props">
					{{ field.value }}
				</component>
			</n-descriptions-item>
		</n-descriptions>
	</div>
</template>

<script setup lang="ts">
import type { BadgeProps } from "naive-ui"
import type { AgentArtifactData } from "@/types/agents.d"
import bytes from "bytes"
import { NBadge, NDescriptions, NDescriptionsItem } from "naive-ui"
import { computed } from "vue"
import { useSettingsStore } from "@/stores/settings"
import { formatDate } from "@/utils/format"

const { artifact } = defineProps<{ artifact: AgentArtifactData }>()

const dFormats = useSettingsStore().dateFormat

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

const fields = computed(() => [
	{
		key: "id",
		label: "ID",
		value: artifact.id,
		component: "code"
	},
	{
		key: "agent_id",
		label: "Agent ID",
		value: artifact.agent_id,
		component: "code"
	},
	{
		key: "velociraptor_id",
		label: "Velociraptor ID",
		value: artifact.velociraptor_id,
		component: "code"
	},
	{
		key: "customer_code",
		label: "Customer Code",
		value: artifact.customer_code || "",
		condition: !!artifact.customer_code
	},
	{
		key: "artifact_name",
		label: "Artifact Name",
		value: artifact.artifact_name
	},
	{
		key: "flow_id",
		label: "Flow ID",
		value: artifact.flow_id,
		component: "code"
	},
	{
		key: "file_name",
		label: "File Name",
		value: artifact.file_name
	},
	{
		key: "file_size",
		label: "File Size",
		value: fileSize.value
	},
	{
		key: "content_type",
		label: "Content Type",
		value: artifact.content_type
	},
	{
		key: "file_hash",
		label: "File Hash",
		value: artifact.file_hash,
		component: "code",
		props: { class: "text-xs" }
	},
	{
		key: "collection_time",
		label: "Collection Time",
		value: formatDate(artifact.collection_time, dFormats.datetime)
	},
	{
		key: "status",
		label: "Status",
		value: artifact.status,
		component: NBadge,
		props: { value: artifact.status, type: statusType.value }
	},
	{
		key: "bucket_name",
		label: "Bucket",
		value: artifact.bucket_name
	},
	{
		key: "object_key",
		label: "Object Key",
		value: artifact.object_key,
		component: "code",
		props: { class: "text-xs" }
	},
	{
		key: "uploaded_by",
		label: "Uploaded By",
		value: artifact.uploaded_by || "",
		condition: !!artifact.uploaded_by
	},
	{
		key: "notes",
		label: "Notes",
		value: artifact.notes || "",
		condition: !!artifact.notes
	}
])

const visibleFields = computed(() => fields.value.filter(field => field.condition !== false))
</script>

<style lang="scss" scoped>
// TODO: remove style
.artifact-details {
	:deep() {
		code {
			font-family: var(--font-family-mono);
			font-size: 12px;
			padding: 2px 4px;
			background-color: var(--bg-secondary-color);
			border-radius: 3px;
		}
	}
}
</style>
