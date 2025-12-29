<template>
	<div class="artifacts-collect">
		<div class="header flex items-start justify-end gap-2">
			<div v-if="isDirty" class="info flex gap-5">
				<n-popover overlap placement="bottom-start">
					<template #trigger>
						<div class="bg-default rounded-lg">
							<n-button size="small" class="cursor-help!">
								<template #icon>
									<Icon :name="InfoIcon" />
								</template>
							</n-button>
						</div>
					</template>
					<div class="flex flex-col gap-2">
						<div class="box">
							Total :
							<code>{{ total }}</code>
						</div>
					</div>
				</n-popover>
			</div>
			<div class="flex grow flex-wrap items-center justify-end gap-2">
				<div v-if="!hideHostnameField" class="grow basis-56">
					<n-select
						v-model:value="filters.hostname"
						:options="agentHostnameOptions"
						placeholder="Agent hostname"
						clearable
						filterable
						:disabled="loading"
						size="small"
						:loading="loadingAgents"
					/>
				</div>
				<div class="grow basis-56">
					<n-select
						v-model:value="filters.artifact_name"
						:options="artifactsOptions"
						placeholder="Artifact name"
						clearable
						:disabled="loading"
						filterable
						size="small"
						:loading="loadingArtifacts"
						@update:value="onArtifactSelect"
					/>
				</div>
				<div v-if="!hideVelociraptorIdField" class="grow basis-56">
					<n-input
						v-model:value="filters.velociraptor_id"
						placeholder="Velociraptor ID"
						clearable
						:readonly="loading"
						size="small"
					/>
				</div>
				<div>
					<n-button
						size="small"
						type="primary"
						secondary
						:loading="loading"
						:disabled="!areFiltersValid"
						@click="getData()"
					>
						Submit
					</n-button>
				</div>
			</div>
		</div>

		<!-- Parameters Section -->
		<div v-if="selectedArtifactParameters.length" class="parameters-section my-4">
			<n-card title="Artifact Parameters" size="small">
				<template #header-extra>
					<n-tag size="small" type="info">
						{{ selectedArtifactParameters.length }} parameter{{ selectedArtifactParameters.length !== 1 ? 's' : '' }}
					</n-tag>
				</template>
				<n-spin :show="loadingParameters">
					<n-scrollbar style="max-height: 400px">
						<div class="parameters-grid">
							<div v-for="param in selectedArtifactParameters" :key="param.name" class="parameter-field">
								<div class="parameter-header">
									<div class="flex items-center gap-2">
										<span class="parameter-name">{{ param.name }}</span>
										<n-tag v-if="param.type" size="tiny" :bordered="false">
											{{ param.type }}
										</n-tag>
									</div>
									<n-popover v-if="param.description" trigger="hover" placement="top">
										<template #trigger>
											<Icon :name="InfoIcon" :size="16" class="cursor-help text-gray-400 hover:text-gray-600" />
										</template>
										<div class="parameter-tooltip">
											<div class="font-medium mb-2">{{ param.name }}</div>
											<div class="text-sm">{{ param.description }}</div>
											<div v-if="param.default" class="text-xs mt-2 opacity-70">
												Default: <code class="bg-gray-100 px-1 rounded">{{ param.default }}</code>
											</div>
										</div>
									</n-popover>
								</div>
								<n-input
									v-model:value="parameterValues[param.name]"
									:placeholder="param.default?.toString() || 'Enter value...'"
									size="small"
									clearable
									class="mt-2"
								>
									<template v-if="param.default" #suffix>
										<n-tooltip trigger="hover" placement="top">
											<template #trigger>
												<n-button
													text
													size="tiny"
													@click="parameterValues[param.name] = escapeBackslashes(param.default?.toString() || '')"
												>
													<Icon name="carbon:reset" :size="14" />
												</n-button>
											</template>
											Reset to default
										</n-tooltip>
									</template>
								</n-input>
								<div v-if="param.description" class="parameter-description">
									{{ param.description }}
								</div>
							</div>
						</div>
					</n-scrollbar>
				</n-spin>
			</n-card>
		</div>

		<n-spin :show="loading">
			<div class="my-7 flex min-h-52 flex-col gap-3">
				<template v-if="collectList.length">
					<CollectItem
						v-for="collect of collectList"
						:key="`${collect.___id}`"
						embedded
						:collect="collect"
						class="item-appear item-appear-bottom item-appear-005"
					/>
				</template>
				<template v-else>
					<n-empty v-if="!loading" description="No items found" class="h-48 justify-center" />
				</template>
			</div>
		</n-spin>
	</div>
</template>

<script setup lang="ts">
import type { ArtifactsQuery, CollectRequest } from "@/api/endpoints/artifacts"
import type { Agent } from "@/types/agents.d"
import type { Artifact, ArtifactParameter, CollectResult } from "@/types/artifacts.d"
import { NButton, NCard, NEmpty, NInput, NPopover, NScrollbar, NSelect, NSpin, NTag, NTooltip, useMessage } from "naive-ui"
import { nanoid } from "nanoid"
import { computed, nextTick, onBeforeMount, ref, toRefs } from "vue"
import Api from "@/api"
import Icon from "@/components/common/Icon.vue"
import CollectItem from "./CollectItem.vue"

const props = defineProps<{
    hostname?: string
    velociraptorId?: string
    agents?: Agent[]
    artifacts?: Artifact[]
    artifactsFilter?: ArtifactsQuery
    hideHostnameField?: boolean
    hideVelociraptorIdField?: boolean
}>()

const emit = defineEmits<{
    (e: "loaded-agents", value: Agent[]): void
    (e: "loaded-artifacts", value: Artifact[]): void
}>()

const { hostname, velociraptorId, agents, artifacts, artifactsFilter, hideHostnameField, hideVelociraptorIdField } =
    toRefs(props)

const message = useMessage()
const loadingAgents = ref(false)
const loadingArtifacts = ref(false)
const loadingParameters = ref(false)
const loading = ref(false)
const agentsList = ref<Agent[]>([])
const artifactsList = ref<Artifact[]>([])
const collectList = ref<CollectResult[]>([])
const isDirty = ref(false)
const selectedArtifactParameters = ref<ArtifactParameter[]>([])
const parameterValues = ref<Record<string, string>>({})

const InfoIcon = "carbon:information"

const total = computed<number>(() => {
    return collectList.value.length || 0
})

const filters = ref<Partial<CollectRequest>>({})

const areFiltersValid = computed(() => {
    return !!filters.value.artifact_name && !!filters.value.hostname
})

const agentHostnameOptions = computed(() => {
    if (hostname?.value) {
        return [{ value: hostname.value, label: hostname.value }]
    }
    return (agentsList.value || []).map(o => ({ value: o.hostname, label: o.hostname }))
})

const artifactsOptions = computed(() => {
    return (artifactsList.value || []).map(o => ({ value: o.name, label: o.name }))
})

// Function to escape backslashes in Windows paths
function escapeBackslashes(value: string): string {
    // Only escape if it looks like a Windows path (contains backslashes)
    if (value && typeof value === 'string' && value.includes('\\')) {
        // Replace single backslashes with double backslashes
        return value.replace(/\\/g, '\\\\')
    }
    return value
}

async function onArtifactSelect(artifactName: string | null) {
    selectedArtifactParameters.value = []
    parameterValues.value = {}

    if (!artifactName) {
        return
    }

    loadingParameters.value = true

    try {
        const res = await Api.artifacts.getByName(artifactName)

        if (res.data.success && res.data.artifacts?.length) {
            const artifact = res.data.artifacts[0]

            if (artifact.parameters?.length) {
                selectedArtifactParameters.value = artifact.parameters

                // Initialize parameter values with defaults (with escaped backslashes)
                artifact.parameters.forEach(param => {
                    if (param.default !== undefined && param.default !== null && param.default !== "") {
                        const defaultValue = param.default.toString()
                        parameterValues.value[param.name] = escapeBackslashes(defaultValue)
                    }
                })
            }
        }
    } catch (err: any) {
        message.error(err.response?.data?.message || "Failed to load artifact parameters")
    } finally {
        loadingParameters.value = false
    }
}

function getData() {
    if (areFiltersValid.value) {
        loading.value = true

        // Build parameters object if any values are set
        const parameters: CollectRequest["parameters"] = {
            env: []
        }

        Object.entries(parameterValues.value).forEach(([key, value]) => {
            if (value !== undefined && value !== null && value !== "") {
                parameters.env!.push({ key, value })
            }
        })

        const payload: CollectRequest = {
            ...filters.value,
            hostname: filters.value.hostname!,
            artifact_name: filters.value.artifact_name!
        }

        // Only add parameters if there are any
        if (parameters.env!.length > 0) {
            payload.parameters = parameters
        }

        Api.artifacts
            .collect(payload)
            .then(res => {
                if (res.data.success) {
                    isDirty.value = true

                    collectList.value = (res.data?.results || []).map(o => {
                        o.___id = nanoid()
                        return o
                    })
                } else {
                    message.warning(res.data?.message || "An error occurred. Please try again later.")
                }
            })
            .catch(err => {
                collectList.value = []

                message.error(err.response?.data?.message || "An error occurred. Please try again later.")
            })
            .finally(() => {
                loading.value = false
            })
    }
}

function getAgents(cb?: (agents: Agent[]) => void) {
    loadingAgents.value = true

    Api.agents
        .getAgents()
        .then(res => {
            if (res.data.success) {
                agentsList.value = res.data.agents || []

                if (cb && typeof cb === "function") {
                    cb(agentsList.value)
                }
            } else {
                message.error(res.data?.message || "An error occurred. Please try again later.")
            }
        })
        .catch(err => {
            message.error(err.response?.data?.message || "An error occurred. Please try again later.")
        })
        .finally(() => {
            loadingAgents.value = false
        })
}

function getArtifacts(cb?: (artifacts: Artifact[]) => void) {
    loadingArtifacts.value = true

    Api.artifacts
        .getAll(artifactsFilter.value)
        .then(res => {
            if (res.data.success) {
                artifactsList.value = res.data.artifacts || []

                if (cb && typeof cb === "function") {
                    cb(artifactsList.value)
                }
            } else {
                message.error(res.data?.message || "An error occurred. Please try again later.")
            }
        })
        .catch(err => {
            message.error(err.response?.data?.message || "An error occurred. Please try again later.")
        })
        .finally(() => {
            loadingArtifacts.value = false
        })
}

onBeforeMount(() => {
    if (hostname?.value) {
        filters.value.hostname = hostname.value
    }

    if (velociraptorId?.value) {
        filters.value.velociraptor_id = velociraptorId.value
    }

    if (agents?.value?.length && !agentsList.value.length) {
        agentsList.value = agents.value
    }

    if (artifacts?.value?.length && !artifactsList.value.length) {
        artifactsList.value = artifacts.value
    }

    nextTick(() => {
        if (!agentsList.value.length && !hostname?.value) {
            getAgents((agents: Agent[]) => {
                emit("loaded-agents", agents)
            })
        }
        if (!artifactsList.value.length) {
            getArtifacts((artifacts: Artifact[]) => {
                emit("loaded-artifacts", artifacts)
            })
        }
    })
})
</script>

<style scoped>
.parameters-grid {
    display: grid;
    gap: 1rem;
    padding: 0.5rem;
}

.parameter-field {
    background-color: #f9fafb;
    border: 1px solid #e5e7eb;
    border-radius: 8px;
    padding: 1rem;
    transition: all 0.2s ease;
}

.parameter-field:hover {
    border-color: #d1d5db;
    box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
}

.parameter-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 0.5rem;
}

.parameter-name {
    font-weight: 600;
    font-size: 0.875rem;
    color: #374151;
}

.parameter-description {
    font-size: 0.75rem;
    color: #6b7280;
    margin-top: 0.5rem;
    line-height: 1.4;
}

.parameter-tooltip {
    max-width: 400px;
}

/* Dark mode support */
@media (prefers-color-scheme: dark) {
    .parameter-field {
        background-color: #1f2937;
        border-color: #374151;
    }

    .parameter-field:hover {
        border-color: #4b5563;
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.2);
    }

    .parameter-name {
        color: #f3f4f6;
    }

    .parameter-description {
        color: #9ca3af;
    }
}
</style>
