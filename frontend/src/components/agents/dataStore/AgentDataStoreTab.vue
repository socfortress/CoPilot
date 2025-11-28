<template>
    <div class="agent-data-store-tab">
        <div class="flex gap-4">
            <div class="filters-section" style="min-width: 280px; max-width: 320px">
                <n-card size="small" title="Filters" :segmented="{ content: true }">
                    <div class="flex flex-col gap-3">
                        <n-input
                            v-model:value="textFilter"
                            placeholder="Search artifacts..."
                            clearable
                            size="small"
                        >
                            <template #prefix>
                                <Icon :name="SearchIcon" :size="16" />
                            </template>
                        </n-input>

                        <n-select
                            v-model:value="statusFilter"
                            :options="statusOptions"
                            placeholder="Filter by status"
                            size="small"
                            clearable
                        />

                        <n-button type="primary" secondary size="small" @click="getArtifacts()" :loading="loading">
                            <template #icon>
                                <Icon :name="RefreshIcon" />
                            </template>
                            Refresh
                        </n-button>

                        <n-divider class="!my-2" />

                        <div class="flex flex-col gap-2 text-sm">
                            <div class="flex items-center justify-between">
                                <span class="text-secondary-color">Total:</span>
                                <span class="font-mono">{{ artifacts.length }}</span>
                            </div>
                            <div class="flex items-center justify-between">
                                <span class="text-secondary-color">Filtered:</span>
                                <span class="font-mono">{{ artifactsFiltered.length }}</span>
                            </div>
                        </div>
                    </div>
                </n-card>
            </div>

            <div class="artifacts-section flex-1">
                <n-spin :show="loading">
                    <n-scrollbar style="max-height: 600px">
                        <div class="flex flex-col gap-3 pr-2">
                            <template v-if="artifactsFiltered.length">
                                <ArtifactCard
                                    v-for="artifact in itemsPaginated"
                                    :key="artifact.id"
                                    :artifact
                                    show-actions
                                    hoverable
                                    @download="downloadArtifact(artifact)"
                                    @delete="deleteArtifact(artifact)"
                                    @details="showArtifactDetails(artifact)"
                                />
                            </template>
                            <template v-else>
                                <n-empty
                                    v-if="!loading"
                                    description="No artifacts found"
                                    class="h-48 justify-center"
                                />
                            </template>
                        </div>
                    </n-scrollbar>

                    <div v-if="artifactsFiltered.length > pageSize" class="mt-4 flex justify-end">
                        <n-pagination
                            v-model:page="page"
                            :page-size="pageSize"
                            :page-slot="5"
                            :item-count="artifactsFiltered.length"
                            size="small"
                        />
                    </div>
                </n-spin>
            </div>
        </div>

        <!-- Artifact Details Modal -->
        <n-modal
            v-model:show="showDetailsModal"
            preset="card"
            title="Artifact Details"
            :style="{ width: '800px' }"
            :segmented="{ content: true }"
        >
            <ArtifactDetails v-if="selectedArtifact" :artifact="selectedArtifact" />
        </n-modal>
    </div>
</template>

<script setup lang="ts">
import type { Agent, AgentArtifactData } from "@/types/agents.d"
import _debounce from "lodash/debounce"
import {
    NButton,
    NCard,
    NDivider,
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
import { computed, onMounted, ref, watch } from "vue"
import Api from "@/api"
import Icon from "@/components/common/Icon.vue"
import ArtifactCard from "./ArtifactCard.vue"
import ArtifactDetails from "./ArtifactDetails.vue"

interface Props {
    agent: Agent
}

const props = defineProps<Props>()

const message = useMessage()
const dialog = useDialog()

const SearchIcon = "carbon:search"
const RefreshIcon = "carbon:renew"

const loading = ref(false)
const artifacts = ref<AgentArtifactData[]>([])
const textFilter = ref("")
const statusFilter = ref<string | null>(null)
const page = ref(1)
const pageSize = ref(20)
const showDetailsModal = ref(false)
const selectedArtifact = ref<AgentArtifactData | null>(null)

const textFilterDebounced = ref("")

const update = _debounce((value: string) => {
    textFilterDebounced.value = value
}, 300)

watch(textFilter, val => {
    update(val)
})

const statusOptions = [
    { label: "All", value: null },
    { label: "Completed", value: "completed" },
    { label: "Failed", value: "failed" },
    { label: "Processing", value: "processing" }
]

const artifactsFiltered = computed(() => {
    return artifacts.value.filter(artifact => {
        // Text filter
        const matchesText =
            (artifact.artifact_name + artifact.flow_id + artifact.file_name)
                .toString()
                .toLowerCase()
                .includes(textFilterDebounced.value.toString().toLowerCase())

        // Status filter
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
        .listAgentArtifacts(props.agent.agent_id)
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
        .downloadAgentArtifact(props.agent.agent_id, artifact.id)
        .then(res => {
            // Create a blob URL and trigger download
            const blob = new Blob([res.data], { type: artifact.content_type })
            const url = window.URL.createObjectURL(blob)
            const link = document.createElement("a")
            link.href = url
            link.download = artifact.file_name
            document.body.appendChild(link)
            link.click()
            document.body.removeChild(link)
            window.URL.revokeObjectURL(url)

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
                .deleteAgentArtifact(props.agent.agent_id, artifact.id)
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
.agent-data-store-tab {
    .filters-section {
        :deep() {
            .n-card__content {
                padding: 16px;
            }
        }
    }

    .artifacts-section {
        min-height: 300px;
    }
}
</style>
