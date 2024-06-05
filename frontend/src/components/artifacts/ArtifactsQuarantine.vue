<template>
	<div class="artifacts-quarantine">
		<div class="header flex justify-end items-start gap-2">
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
						placeholder="Velociraptor id"
						clearable
						:readonly="loading"
						size="small"
					/>
				</div>
				<div>
					<n-input-group>
						<n-select
							v-model:value="filters.action"
							:options="actionsOptions"
							:disabled="loading"
							size="small"
							class="!w-32"
							status="success"
						/>
						<n-button
							size="small"
							@click="getData()"
							type="primary"
							secondary
							:loading="loading"
							:disabled="!areFiltersValid"
						>
							<Icon :name="SubmitIcon"></Icon>
						</n-button>
					</n-input-group>
				</div>
			</div>
		</div>
		<n-spin :show="loading">
			<div class="list grid gap-3 my-7">
				<template v-if="quarantineList.length">
					<QuarantineItem
						v-for="quarantine of quarantineList"
						:key="quarantine.Result + quarantine.Time"
						:quarantine="quarantine"
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
import { useMessage, NSpin, NButton, NEmpty, NSelect, NInput, NInputGroup } from "naive-ui"
import Api from "@/api"
import Icon from "@/components/common/Icon.vue"
import QuarantineItem from "./QuarantineItem.vue"
import type { Agent } from "@/types/agents.d"
import type { QuarantineRequest } from "@/api/artifacts"
import type { Artifact, QuarantineResult } from "@/types/artifacts.d"
// import { quarantineResult } from "./mock"

const emit = defineEmits<{
	(e: "loaded-agents", value: Agent[]): void
	(e: "loaded-artifacts", value: Artifact[]): void
	(e: "action-performed"): void
}>()

const props = defineProps<{
	hostname?: string
	agents?: Agent[]
	artifacts?: Artifact[]
	hideHostnameField?: boolean
	hideVelociraptorIdField?: boolean
}>()
const { hostname, agents, artifacts, hideHostnameField, hideVelociraptorIdField } = toRefs(props)

const message = useMessage()
const loadingAgents = ref(false)
const loadingArtifacts = ref(false)
const loading = ref(false)
const agentsList = ref<Agent[]>([])
const artifactsList = ref<Artifact[]>([])
const quarantineList = ref<QuarantineResult[]>([])

const SubmitIcon = "carbon:play"

const filters = ref<Partial<QuarantineRequest>>({})

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

const actionsOptions = ref([
	{ label: "Quarantine", value: "quarantine" },
	{ label: "Remove", value: "remove_quarantine" }
])

function getData() {
	if (areFiltersValid.value) {
		loading.value = true

		Api.artifacts
			.quarantine(filters.value as QuarantineRequest)
			.then(res => {
				if (res.data.success) {
					quarantineList.value = res.data?.results || []
					emit("action-performed")
				} else {
					message.warning(res.data?.message || "An error occurred. Please try again later.")
				}
			})
			.catch(err => {
				quarantineList.value = []

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
		.getAll()
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
	artifactsList.value = ["Windows.Remediation.Quarantine", "Linux.Remediation.Quarantine"].map(
		o => ({ name: o }) as Artifact
	)

	if (hostname?.value) {
		filters.value.hostname = hostname.value
	}

	if (agents?.value?.length && !agentsList.value.length) {
		agentsList.value = agents.value
	}

	if (artifacts?.value?.length && !artifactsList.value.length) {
		artifactsList.value = artifacts.value
	}

	filters.value.action = actionsOptions.value[0].value as QuarantineRequest["action"]

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
	// quarantineList.value = quarantineResult as QuarantineResult[]
})
</script>

<style lang="scss" scoped>
.artifacts-quarantine {
	.list {
		container-type: inline-size;
		min-height: 100px;
	}
}
</style>
