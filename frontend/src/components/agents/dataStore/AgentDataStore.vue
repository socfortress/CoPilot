<template>
	<div class="flex flex-col gap-4">
		<div class="flex flex-wrap items-center gap-6">
			<div class="flex grow items-center gap-2">
				<n-input
					v-model:value="textFilter"
					placeholder="Search artifacts..."
					clearable
					size="small"
					class="min-w-45"
				>
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
					class="max-w-40 min-w-20"
					:consistent-menu-width="false"
				/>
			</div>

			<div class="text-secondary ml-auto flex shrink-0 items-center gap-3 text-xs tracking-wide uppercase">
				<span>
					Total:
					<strong class="text-default font-mono">{{ artifacts.length }}</strong>
				</span>
				<span>
					Filtered:
					<strong class="text-default font-mono">{{ artifactsFiltered.length }}</strong>
				</span>
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
import { NEmpty, NInput, NModal, NPagination, NSelect, NSpin, useDialog, useMessage } from "naive-ui"
import { computed, ref, watch } from "vue"
import Api from "@/api"
import Icon from "@/components/common/Icon.vue"
import AgentArtifactCard from "./AgentArtifactCard.vue"
import ArtifactDetails from "./ArtifactDetails.vue"

const { agentId } = defineProps<{
	agentId: string
}>()

const message = useMessage()
const dialog = useDialog()

const SearchIcon = "carbon:search"

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
				artifacts.value = res.data.data || []
				return
			}
			message.error(res.data?.message || "An error occurred. Please try again later.")
			artifacts.value = []
		})
		.catch(err => {
			message.error(err.response?.data?.message || "An error occurred. Please try again later.")
			artifacts.value = []
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
