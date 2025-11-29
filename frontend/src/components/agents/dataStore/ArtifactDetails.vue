<template>
	<div class="artifact-details flex flex-col gap-4">
		<n-descriptions :column="1" bordered size="small">
			<n-descriptions-item label="ID">
				<code>{{ artifact.id }}</code>
			</n-descriptions-item>
			<n-descriptions-item label="Agent ID">
				<code>{{ artifact.agent_id }}</code>
			</n-descriptions-item>
			<n-descriptions-item label="Velociraptor ID">
				<code>{{ artifact.velociraptor_id }}</code>
			</n-descriptions-item>
			<n-descriptions-item v-if="artifact.customer_code" label="Customer Code">
				{{ artifact.customer_code }}
			</n-descriptions-item>
			<n-descriptions-item label="Artifact Name">
				{{ artifact.artifact_name }}
			</n-descriptions-item>
			<n-descriptions-item label="Flow ID">
				<code>{{ artifact.flow_id }}</code>
			</n-descriptions-item>
			<n-descriptions-item label="File Name">
				{{ artifact.file_name }}
			</n-descriptions-item>
			<n-descriptions-item label="File Size">
				{{ fileSize }}
			</n-descriptions-item>
			<n-descriptions-item label="Content Type">
				{{ artifact.content_type }}
			</n-descriptions-item>
			<n-descriptions-item label="File Hash">
				<code class="text-xs">{{ artifact.file_hash }}</code>
			</n-descriptions-item>
			<n-descriptions-item label="Collection Time">
				{{ formatDate(artifact.collection_time, dFormats.datetime) }}
			</n-descriptions-item>
			<n-descriptions-item label="Status">
				<n-badge :value="artifact.status" :type="getStatusType(artifact.status)" />
			</n-descriptions-item>
			<n-descriptions-item label="Bucket">
				{{ artifact.bucket_name }}
			</n-descriptions-item>
			<n-descriptions-item label="Object Key">
				<code class="text-xs">{{ artifact.object_key }}</code>
			</n-descriptions-item>
			<n-descriptions-item v-if="artifact.uploaded_by" label="Uploaded By">
				{{ artifact.uploaded_by }}
			</n-descriptions-item>
			<n-descriptions-item v-if="artifact.notes" label="Notes">
				{{ artifact.notes }}
			</n-descriptions-item>
		</n-descriptions>
	</div>
</template>

<script setup lang="ts">
import type { AgentArtifactData } from "@/types/agents.d"
import bytes from "bytes"
import { NBadge, NDescriptions, NDescriptionsItem } from "naive-ui"
import { computed } from "vue"
import { useSettingsStore } from "@/stores/settings"
import { formatDate } from "@/utils"

	const { artifact } = defineProps<{ artifact: AgentArtifactData }>()

const dFormats = useSettingsStore().dateFormat

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
