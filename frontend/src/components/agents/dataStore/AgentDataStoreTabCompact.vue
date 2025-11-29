<template>
	<div class="agent-data-store-tab-compact">
		<div class="flex flex-col gap-3">
			<div class="filters-bar flex flex-wrap items-center gap-2">
				<n-input
					v-model:value="textFilter"
					placeholder="Search artifacts..."
					clearable
					size="small"
					style="max-width: 250px"
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
					style="max-width: 150px"
				/>

				<n-button type="primary" secondary size="small" :loading="loading" @click="getArtifacts()">
					<template #icon>
						<Icon :name="RefreshIcon" />
					</template>
				</n-button>

				<div class="flex-1"></div>

				<div class="flex items-center gap-3 text-xs text-secondary-color">
					<span>Total: <strong class="font-mono">{{ artifacts.length }}</strong></span>
					<span>Filtered: <strong class="font-mono">{{ artifactsFiltered.length }}</strong></span>
				</div>
			</div>

			<n-spin :show="loading">
				<div class="artifacts-list">
					<n-scrollbar style="max-height: 400px">
						<div class="flex flex-col gap-2 pr-2">
							<template v-if="artifactsFiltered.length">
								<ArtifactCardCompact
									v-for="artifact in itemsPaginated"
									:key="artifact.id"
									:artifact
									show-actions
									@download="downloadArtifact(artifact)"
									@delete="deleteArtifact(artifact)"
									@details="showArtifactDetails(artifact)"
								/>
							</template>
							<template v-else>
								<n-empty
									v-if="!loading"
									description="No artifacts found"
									class="h-32 justify-center"
									size="small"
								/>
							</template>
						</div>
					</n-scrollbar>

					<div v-if="artifactsFiltered.length > pageSize" class="mt-3 flex justify-end">
						<n-pagination
							v-model:page="page"
							:page-size="pageSize"
							:page-slot="5"
							:item-count="artifactsFiltered.length"
							size="small"
						/>
					</div>
				</div>
			</n-spin>
		</div>

		<!-- Artifact Details Modal -->
		<n-modal
			v-model:show="showDetailsModal"
			preset="card"
			title="Artifact Details"
			:style="{ width: '700px' }"
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
import {
    NButton,
    NEmpty,
    NInput,
    NModal,
    NPagination,
    NScrollbar,
    NSelect,
    NSpin,
    useDialog,
	useMessage
} from "naive-ui"
	import { computed, onMounted, ref } from "vue"
import Api from "@/api"
import Icon from "@/components/common/Icon.vue"
import ArtifactCardCompact from "./ArtifactCardCompact.vue"
import ArtifactDetails from "./ArtifactDetails.vue"

const props = defineProps<{
    agentId: string
}>()

const message = useMessage()
const dialog = useDialog()

const SearchIcon = "carbon:search"
const RefreshIcon = "carbon:renew"

const loading = ref(false)
const artifacts = ref<AgentArtifactData[]>([])
	const textFilter = ref<string | null>(null)
const textFilterDebounced = refDebounced<string | null>(textFilter, 300)
const statusFilter = ref<string | null>(null)
const page = ref(1)
const pageSize = ref(10)
const showDetailsModal = ref(false)
const selectedArtifact = ref<AgentArtifactData | null>(null)

const statusOptions: SelectOption[] = [
    { label: "All", value: undefined },
    { label: "Completed", value: "completed" },
    { label: "Failed", value: "failed" },
    { label: "Processing", value: "processing" }
]

const artifactsFiltered = computed(() => {
    return artifacts.value.filter(artifact => {
        const matchesText =
            (artifact.artifact_name + artifact.flow_id + artifact.file_name)
                .toString()
                .toLowerCase()
                .includes((textFilterDebounced.value || '').toString().toLowerCase())

        const matchesStatus = !statusFilter.value || artifact.status === statusFilter.value

        return matchesText && matchesStatus
    })
})

const itemsPaginated = computed(() => {
    const from = (page.value - 1) * pageSize.value
    const to = page.value * pageSize.value

    return artifactsFiltered.value.slice(from, to)
})

function getArtifacts() {
    loading.value = true

    Api.agents
        .listAgentArtifacts(props.agentId)
        .then(res => {
            if (res.data.success) {
                artifacts.value = res.data.data || []
            } else {
                message.error(res.data?.message || "An error occurred. Please try again later.")
            }
        })
        .catch(err => {
            message.error(err.response?.data?.message || "An error occurred. Please try again later.")
        })
        .finally(() => {
            loading.value = false
        })
}

function downloadArtifact(artifact: AgentArtifactData) {
    message.loading(`Downloading ${artifact.file_name}...`)

    Api.agents
        .downloadAgentArtifact(props.agentId, artifact.id)
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
        content: `Are you sure you want to delete "${artifact.file_name}"? This action cannot be undone.`,
        positiveText: "Delete",
        negativeText: "Cancel",
        onPositiveClick: () => {
            Api.agents
                .deleteAgentArtifact(props.agentId, artifact.id)
                .then(res => {
                    if (res.data.success) {
                        message.success("Artifact deleted successfully")
                        getArtifacts()
                    } else {
                        message.error(res.data?.message || "Failed to delete artifact")
                    }
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

onMounted(() => {
    getArtifacts()
})
</script>

<style lang="scss" scoped>
// TODO: remove style

.agent-data-store-tab-compact {
    .filters-bar {
        padding-bottom: 8px;
        border-bottom: 1px solid var(--border-color);
    }

    .artifacts-list {
        min-height: 200px;
    }
}
</style>
