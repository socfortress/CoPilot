<template>
	<div class="artifacts-collect">
		<div class="header flex justify-end items-start gap-2">
			<div class="info flex gap-5" v-if="isDirty">
				<n-popover overlap placement="bottom-start">
					<template #trigger>
						<div class="bg-color border-radius">
							<n-button size="small" class="!cursor-help">
								<template #icon>
									<Icon :name="InfoIcon"></Icon>
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
			<div class="grow flex items-center justify-end gap-2 flex-wrap">
				<div class="grow basis-56" v-if="!hideHostnameField">
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
					/>
				</div>
				<div class="grow basis-56" v-if="!hideVelociraptorIdField">
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
						@click="getData()"
						type="primary"
						secondary
						:loading="loading"
						:disabled="!areFiltersValid"
					>
						Submit
					</n-button>
				</div>
			</div>
		</div>
		<n-spin :show="loading">
			<div class="list grid gap-3 my-7">
				<template v-if="collectList.length">
					<CollectItem
						v-for="collect of collectList"
						:key="collect.___id"
						:collect="collect"
						class="item-appear item-appear-bottom item-appear-005"
					/>
				</template>
				<template v-else>
					<n-empty description="No items found" class="justify-center h-48" v-if="!loading" />
				</template>
			</div>
		</n-spin>
	</div>
</template>

<script setup lang="ts">
import { ref, onBeforeMount, toRefs, computed, nextTick } from "vue"
import { useMessage, NSpin, NPopover, NButton, NEmpty, NSelect, NInput } from "naive-ui"
import Api from "@/api"
import Icon from "@/components/common/Icon.vue"
import CollectItem from "./CollectItem.vue"
import type { Agent } from "@/types/agents.d"
import type { ArtifactsQuery, CollectRequest } from "@/api/artifacts"
import type { Artifact, CollectResult } from "@/types/artifacts.d"
import { nanoid } from "nanoid"
// import { collectResult } from "./mock"

const emit = defineEmits<{
	(e: "loaded-agents", value: Agent[]): void
	(e: "loaded-artifacts", value: Artifact[]): void
}>()

const props = defineProps<{
	hostname?: string
	velociraptorId?: string
	agents?: Agent[]
	artifacts?: Artifact[]
	artifactsFilter?: ArtifactsQuery
	hideHostnameField?: boolean
	hideVelociraptorIdField?: boolean
}>()
const { hostname, velociraptorId, agents, artifacts, artifactsFilter, hideHostnameField, hideVelociraptorIdField } =
	toRefs(props)

const message = useMessage()
const loadingAgents = ref(false)
const loadingArtifacts = ref(false)
const loading = ref(false)
const agentsList = ref<Agent[]>([])
const artifactsList = ref<Artifact[]>([])
const collectList = ref<CollectResult[]>([])
const isDirty = ref(false)

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

function getData() {
	if (areFiltersValid.value) {
		loading.value = true

		Api.artifacts
			.collect(filters.value as CollectRequest)
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

	// MOCK
	/*
	collectList.value = collectResult.map(o => {
		// @ts-ignore
		o.___id = nanoid()
		return o
	}) as CollectResultExt[]
	*/
})
</script>

<style lang="scss" scoped>
.artifacts-collect {
	.list {
		container-type: inline-size;
		min-height: 200px;
		grid-template-columns: repeat(auto-fit, minmax(390px, 1fr));
		grid-auto-flow: row dense;
	}

	@media (max-width: 490px) {
		.list {
			display: flex;
			flex-direction: column;
		}
	}
}
</style>
