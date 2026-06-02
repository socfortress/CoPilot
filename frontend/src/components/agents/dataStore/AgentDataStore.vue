<template>
	<div class="flex flex-col gap-4">
		<div
			class="border-default bg-secondary/20 flex flex-wrap items-end justify-between gap-3 rounded-lg border p-3 @container"
		>
			<div class="flex flex-wrap items-end gap-2">
				<n-input v-model:value="textFilter" placeholder="Search artifacts..." clearable size="small" class="w-64 max-w-full">
					<template #prefix>
						<Icon :name="SearchIcon" :size="14" />
					</template>
				</n-input>

				<n-select
					v-model:value="statusFilter"
					:options="statusOptions"
					placeholder="Status"
					size="small"
					clearable
					class="w-44 max-w-full"
				/>

				<n-button size="small" secondary :loading @click="getArtifacts()">
					<template #icon>
						<Icon :name="RefreshIcon" />
					</template>
				</n-button>
			</div>

			<div class="flex items-center gap-2 text-xs">
				<n-tag size="small" :bordered="false">TOTAL {{ artifacts.length }}</n-tag>
				<n-tag size="small" :bordered="false">FILTERED {{ artifactsFiltered.length }}</n-tag>
			</div>
		</div>

		<n-spin :show="loading">
			<div class="flex flex-col gap-3">
				<template v-if="artifactsFiltered.length">
					<AgentArtifactCard
						v-for="artifact in itemsPaginated"
						:key="artifact.id"
						:artifact
						show-actions
						hoverable
						@click="showArtifactDetails(artifact)"
						@download="downloadArtifact(artifact)"
						@delete="deleteArtifact(artifact)"
						@details="showArtifactDetails(artifact)"
					/>
				</template>
				<n-empty v-else-if="!loading" description="No artifacts found" class="h-40 justify-center" />
			</div>

			<div v-if="artifactsFiltered.length > pageSize" class="mt-3 flex justify-end">
				<n-pagination
					v-model:page="page"
					:page-size
					:page-slot="5"
					:item-count="artifactsFiltered.length"
					size="small"
				/>
			</div>
		</n-spin>

		<n-modal
			v-model:show="showDetailsModal"
			preset="card"
			title="Artifact Details"
			:style="{ maxWidth: 'min(860px, 92vw)' }"
			:segmented="{ content: true }"
		>
			<ArtifactDetails v-if="selectedArtifact" :artifact="selectedArtifact" />
		</n-modal>
	</div>
</template>

<script setup lang="ts">
import type { SelectOption } from "naive-ui"
import type { AgentArtifactData } from "@/types/agents.d"
import { refDebounced } from "@vueuse/core"
import { saveAs } from "file-saver"
import { NButton, NEmpty, NInput, NModal, NPagination, NSelect, NSpin, NTag, useDialog, useMessage } from "naive-ui"
import { computed, ref, watch } from "vue"
import Api from "@/api"
import Icon from "@/components/common/Icon.vue"
import AgentArtifactCard from "./AgentArtifactCard.vue"
import ArtifactDetails from "./ArtifactDetails.vue"
import { mockAgentArtifacts } from "./mockAgentArtifacts"

const { agentId } = defineProps<{
	agentId: string
}>()

const message = useMessage()
const dialog = useDialog()

const SearchIcon = "carbon:search"
const RefreshIcon = "carbon:renew"

const loading = ref(false)
const artifacts = ref<AgentArtifactData[]>([])
const textFilter = ref<string | null>(null)
const textFilterDebounced = refDebounced<string | null>(textFilter, 250)
const statusFilter = ref<string | null>(null)
const page = ref(1)
const pageSize = ref(12)
const showDetailsModal = ref(false)
const selectedArtifact = ref<AgentArtifactData | null>(null)

const statusOptions: SelectOption[] = [
	{ label: "Completed", value: "completed" },
	{ label: "Failed", value: "failed" },
	{ label: "Processing", value: "processing" }
]

const artifactsFiltered = computed(() => {
	return artifacts.value.filter(artifact => {
		const normalizedSearch = (textFilterDebounced.value || "").toLowerCase().trim()
		const matchesText = [artifact.artifact_name, artifact.flow_id, artifact.file_name, artifact.customer_code]
			.filter(Boolean)
			.join(" ")
			.toLowerCase()
			.includes(normalizedSearch)
		const matchesStatus = !statusFilter.value || artifact.status === statusFilter.value
		return matchesText && matchesStatus
	})
})

const itemsPaginated = computed(() => {
	const from = (page.value - 1) * pageSize.value
	return artifactsFiltered.value.slice(from, from + pageSize.value)
})

function getArtifacts() {
	loading.value = true

	Api.agents
		.listAgentArtifacts(agentId)
		.then(res => {
			if (res.data.success) {
				artifacts.value = mockAgentArtifacts
				return
			}
			message.error(res.data?.message || "An error occurred. Please try again later.")
			artifacts.value = mockAgentArtifacts
		})
		.catch(err => {
			message.error(err.response?.data?.message || "An error occurred. Please try again later.")
			artifacts.value = mockAgentArtifacts
		})
		.finally(() => {
			loading.value = false
		})
}

function downloadArtifact(artifact: AgentArtifactData) {
	message.loading(`Downloading ${artifact.file_name}...`)
	Api.agents
		.downloadAgentArtifact(agentId, artifact.id)
		.then(res => {
			saveAs(res.data, artifact.file_name)
			message.success(`Downloaded ${artifact.file_name}`)
		})
		.catch(err => {
			message.error(err.response?.data?.message || "Failed to download artifact")
		})
}

function deleteArtifact(artifact: AgentArtifactData) {
	dialog.warning({
		title: "Delete Artifact",
		content: `Delete "${artifact.file_name}" permanently?`,
		positiveText: "Delete",
		negativeText: "Cancel",
		onPositiveClick: () => {
			Api.agents
				.deleteAgentArtifact(agentId, artifact.id)
				.then(res => {
					if (res.data.success) {
						message.success("Artifact deleted successfully")
						getArtifacts()
						return
					}
					message.error(res.data?.message || "Failed to delete artifact")
				})
				.catch(err => {
					message.error(err.response?.data?.message || "Failed to delete artifact")
				})
		}
	})
}

function showArtifactDetails(artifact: AgentArtifactData) {
	selectedArtifact.value = artifact
	showDetailsModal.value = true
}

watch(
	() => [textFilterDebounced.value, statusFilter.value] as const,
	() => {
		page.value = 1
	}
)

watch(
	() => agentId,
	() => {
		page.value = 1
		textFilter.value = null
		statusFilter.value = null
		getArtifacts()
	},
	{ immediate: true }
)
</script>
