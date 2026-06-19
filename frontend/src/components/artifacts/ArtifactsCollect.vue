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
					<n-tooltip trigger="hover" placement="top">
						<template #trigger>
							<n-checkbox v-model:checked="filters.data_store_only" :disabled="loading" size="small">
								Store Only
							</n-checkbox>
						</template>
						<div class="text-xs">
							Skip rendering results in frontend and only store the artifact in the data store.
							<br />
							This is faster for large collections.
						</div>
					</n-tooltip>
				</div>
				<div>
					<n-button
						size="small"
						type="primary"
						secondary
						:loading
						:disabled="!areFiltersValid"
						@click="getData()"
					>
						Submit
					</n-button>
				</div>
			</div>
		</div>

		<CardEntity
			v-if="selectedArtifactParameters.length"
			embedded
			size="small"
			:loading="loadingParameters"
			class="my-4"
		>
			<template #headerMain>
				<span class="text-xs font-semibold uppercase">Artifact Parameters</span>
			</template>
			<template #headerExtra>
				<Badge type="splitted" size="small">
					<template #label>Parameters</template>
					<template #value>
						<span class="text-xs">{{ selectedArtifactParameters.length }}</span>
					</template>
				</Badge>
			</template>

			<n-scrollbar class="max-h-100">
				<div class="grid grid-cols-1 gap-3 lg:grid-cols-2">
					<CardEntity
						v-for="param in selectedArtifactParameters"
						:key="param.name"
						embedded
						size="small"
						class="h-full"
						main-box-class="grow"
						card-entity-wrapper-class="h-full"
					>
						<template #headerMain>
							<span class="font-mono text-sm font-semibold">{{ param.name }}</span>
						</template>
						<template v-if="param.type" #headerExtra>
							<Badge size="small">
								<template #value>
									<span class="text-xs">{{ param.type }}</span>
								</template>
							</Badge>
						</template>

						<template v-if="param.description" #default>
							<p class="text-secondary text-xs leading-relaxed">{{ param.description }}</p>
						</template>

						<template #footer>
							<div class="flex flex-col gap-2">
								<div
									v-if="param.default !== null && param.default !== undefined && param.default !== ''"
									class="text-xs opacity-60"
								>
									<span class="font-medium">Default:</span>
									<code class="code-block ml-1 rounded px-1 py-0.5 font-mono text-xs">
										{{ param.default }}
									</code>
								</div>
								<n-input
									v-model:value="parameterValues[param.name]"
									:placeholder="param.default?.toString() || 'Enter value...'"
									size="small"
									clearable
								>
									<template v-if="param.default" #suffix>
										<n-tooltip trigger="hover" placement="top">
											<template #trigger>
												<n-button
													text
													size="tiny"
													@click="
														parameterValues[param.name] = escapeBackslashes(
															param.default?.toString() || ''
														)
													"
												>
													<Icon name="carbon:reset" :size="14" />
												</n-button>
											</template>
											Reset to default
										</n-tooltip>
									</template>
								</n-input>
							</div>
						</template>
					</CardEntity>
				</div>
			</n-scrollbar>
		</CardEntity>

		<n-spin :show="loading">
			<div class="my-7 flex min-h-52 flex-col gap-3">
				<template v-if="filters.data_store_only && isDirty">
					<n-alert
						type="success"
						title="Artifact Stored Successfully"
						class="item-appear item-appear-bottom item-appear-005"
					>
						The artifact has been collected and stored in the data store. Results were not retrieved to
						improve performance.
					</n-alert>
				</template>
				<template v-else-if="collectList.length">
					<CollectItem
						v-for="collect of collectList"
						:key="`${collect.___id}`"
						embedded
						:collect
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
import type { ApiError } from "@/types/common"
import {
	NAlert,
	NButton,
	NCheckbox,
	NEmpty,
	NInput,
	NPopover,
	NScrollbar,
	NSelect,
	NSpin,
	NTooltip,
	useMessage
} from "naive-ui"
import { nanoid } from "nanoid"
import { computed, nextTick, onBeforeMount, ref, toRefs } from "vue"
import Api from "@/api"
import Badge from "@/components/common/Badge.vue"
import CardEntity from "@/components/common/cards/CardEntity.vue"
import Icon from "@/components/common/Icon.vue"
import { getApiErrorMessage } from "@/utils"
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

const filters = ref<Partial<CollectRequest>>({
	data_store_only: false
})

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

const WINDOWS_PATH_BACKSLASH_REGEX = /\\/g

// Function to escape backslashes in Windows paths
function escapeBackslashes(value: string): string {
	// Only escape if it looks like a Windows path (contains backslashes)
	if (value && typeof value === "string" && value.includes("\\")) {
		// Replace single backslashes with double backslashes
		return value.replace(WINDOWS_PATH_BACKSLASH_REGEX, "\\\\")
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

			if (artifact?.parameters?.length) {
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
	} catch (err) {
		message.error(getApiErrorMessage(err as ApiError) || "Failed to load artifact parameters")
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
				parameters.env?.push({ key, value })
			}
		})

		const payload: CollectRequest = {
			...filters.value,
			hostname: filters.value.hostname || "",
			artifact_name: filters.value.artifact_name || "",
			data_store_only: filters.value.data_store_only || false
		}

		// Only add parameters if there are any
		if (parameters.env?.length && parameters.env.length > 0) {
			payload.parameters = parameters
		}

		Api.artifacts
			.collect(payload)
			.then(res => {
				if (res.data.success) {
					isDirty.value = true

					// If data_store_only, results will be null/empty
					if (filters.value.data_store_only) {
						collectList.value = []
						message.success(res.data?.message || "Artifact stored successfully")
					} else {
						collectList.value = (res.data?.results || []).map(o => {
							o.___id = nanoid()
							return o
						})
					}
				} else {
					message.warning(res.data?.message || "An error occurred. Please try again later.")
				}
			})
			.catch(err => {
				collectList.value = []

				message.error(getApiErrorMessage(err as ApiError) || "An error occurred. Please try again later.")
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
			message.error(getApiErrorMessage(err as ApiError) || "An error occurred. Please try again later.")
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
			message.error(getApiErrorMessage(err as ApiError) || "An error occurred. Please try again later.")
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
