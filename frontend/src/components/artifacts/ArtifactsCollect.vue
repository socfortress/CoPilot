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
                <n-spin :show="loadingParameters">
                    <div class="flex flex-col gap-3">
                        <div v-for="param in selectedArtifactParameters" :key="param.name" class="parameter-field">
                            <n-form-item :label="param.name" :label-props="{ style: 'font-weight: 500' }">
                                <template #label>
                                    <div class="flex items-center gap-2">
                                        <span>{{ param.name }}</span>
                                        <n-popover v-if="param.description" trigger="hover" placement="top">
                                            <template #trigger>
                                                <Icon :name="InfoIcon" :size="14" class="cursor-help opacity-60" />
                                            </template>
                                            <div class="max-w-sm">
                                                <div v-if="param.description" class="mb-2">
                                                    {{ param.description }}
                                                </div>
                                                <div v-if="param.type" class="text-xs opacity-70">
                                                    Type: <code>{{ param.type }}</code>
                                                </div>
                                            </div>
                                        </n-popover>
                                    </div>
                                </template>
                                <n-input
                                    v-model:value="parameterValues[param.name]"
                                    :placeholder="param.default?.toString() || ''"
                                    size="small"
                                    clearable
                                />
                            </n-form-item>
                        </div>
                    </div>
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
import { NButton, NCard, NEmpty, NFormItem, NInput, NPopover, NSelect, NSpin, useMessage } from "naive-ui"
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

                // Initialize parameter values with defaults
                artifact.parameters.forEach(param => {
                    if (param.default !== undefined && param.default !== null && param.default !== "") {
                        parameterValues.value[param.name] = param.default.toString()
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
.parameter-field {
    border-bottom: 1px solid #e5e7eb;
    padding-bottom: 0.75rem;
}

.parameter-field:last-child {
    border-bottom: none;
    padding-bottom: 0;
}

/* Dark mode support if needed */
@media (prefers-color-scheme: dark) {
    .parameter-field {
        border-bottom-color: #374151;
    }
}
</style>
