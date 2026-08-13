<template>
	<div>
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
					<EntityDetailsButton
						size="small"
						view-label="Details"
						:route="routeAgentArtifact(agentId, artifact.id)"
						@view="showDetailsModal = true"
					/>
					<n-button size="small" secondary :loading="downloading" @click.stop="downloadArtifact()">
						<template #icon>
							<Icon :name="DownloadIcon" :size="14" />
						</template>
						Download
					</n-button>
					<n-button size="small" ghost type="error" :loading="deleting" @click.stop="deleteArtifact()">
						<template #icon>
							<Icon :name="DeleteIcon" :size="14" />
						</template>
						Delete
					</n-button>
				</div>
			</template>
		</CardEntity>

		<n-modal
			v-model:show="showDetailsModal"
			preset="card"
			title="Artifact Details"
			:style="{ maxWidth: 'min(860px, 92vw)' }"
			:segmented="{ content: true }"
		>
			<ArtifactDetails :artifact />
		</n-modal>
	</div>
</template>

<script setup lang="ts">
import type { TagProps } from "naive-ui"
import type { AgentArtifactData } from "@/types/agents"
import type { ApiError } from "@/types/common"
import { saveAs } from "file-saver"
import { NButton, NModal, NTag, useDialog, useMessage } from "naive-ui"
import { computed, ref } from "vue"
import Api from "@/api"
import Badge from "@/components/common/Badge.vue"
import CardEntity from "@/components/common/cards/CardEntity.vue"
import EntityDetailsButton from "@/components/common/EntityDetailsButton.vue"
import Icon from "@/components/common/Icon.vue"
import { useNavigation } from "@/composables/useNavigation"
import { useSettingsStore } from "@/stores/settings"
import { getApiErrorMessage } from "@/utils"
import { formatBytes, formatDate } from "@/utils/format"
import ArtifactDetails from "./ArtifactDetails.vue"

const {
	artifact,
	agentId,
	showActions = true,
	hoverable = true,
	clickable = false,
	embedded = true
} = defineProps<{
	artifact: AgentArtifactData
	/** Owner agent — required for the self-contained download / delete actions. */
	agentId: string
	showActions?: boolean
	hoverable?: boolean
	clickable?: boolean
	embedded?: boolean
}>()

const emit = defineEmits<{
	(e: "click", artifact: AgentArtifactData): void
	(e: "deleted", artifact: AgentArtifactData): void
}>()

const message = useMessage()
const dialog = useDialog()
const dFormats = useSettingsStore().dateFormat
const { routeAgentArtifact } = useNavigation()

const DownloadIcon = "carbon:download"
const DeleteIcon = "carbon:trash-can"

const showDetailsModal = ref(false)
const downloading = ref(false)
const deleting = ref(false)

const STATUS_TYPE_MAP: Record<string, TagProps["type"]> = {
	completed: "success",
	failed: "error",
	processing: "warning",
	pending: "info"
} as const

const fileSize = computed(() => formatBytes(artifact.file_size))
const statusType = computed<TagProps["type"]>(() => STATUS_TYPE_MAP[artifact.status?.toLowerCase()] ?? "default")

function downloadArtifact() {
	downloading.value = true
	message.loading(`Downloading ${artifact.file_name}...`)

	Api.agents
		.downloadAgentArtifact(agentId, artifact.id)
		.then(res => {
			saveAs(res.data, artifact.file_name)
			message.success(`Downloaded ${artifact.file_name}`)
		})
		.catch(err => {
			message.error(getApiErrorMessage(err as ApiError) || "Failed to download artifact")
		})
		.finally(() => {
			downloading.value = false
		})
}

function deleteArtifact() {
	dialog.warning({
		title: "Delete Artifact",
		content: `Delete "${artifact.file_name}" permanently?`,
		positiveText: "Delete",
		negativeText: "Cancel",
		onPositiveClick: () => {
			deleting.value = true

			Api.agents
				.deleteAgentArtifact(agentId, artifact.id)
				.then(res => {
					if (res.data.success) {
						message.success("Artifact deleted successfully")
						emit("deleted", artifact)
						return
					}
					message.error(res.data?.message || "Failed to delete artifact")
				})
				.catch(err => {
					message.error(getApiErrorMessage(err as ApiError) || "Failed to delete artifact")
				})
				.finally(() => {
					deleting.value = false
				})
		}
	})
}
</script>
