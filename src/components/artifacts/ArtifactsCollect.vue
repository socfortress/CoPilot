<template>
	<div class="artifacts-collect">
		<div class="header flex justify-end items-start gap-2">
			<div class="info flex gap-5">
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
				<div class="grow basis-56">
					<n-select
						v-if="!isFilterPreselected"
						v-model:value="filters.hostname"
						:options="agentHostnameOptions"
						placeholder="Agent hostname"
						clearable
						filterable
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
						filterable
						size="small"
						:loading="loadingArtifacts"
					/>
				</div>
				<div class="grow basis-56">
					<n-input
						v-model:value="filters.velociraptor_id"
						placeholder="Velociraptor id"
						clearable
						size="small"
					/>
				</div>
				<div class="">
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
			<div class="list flex flex-wrap gap-3 my-7">
				<template v-if="collectList.length">
					<CollectItem v-for="collect of collectList" :key="collect.Name" :collect="collect" />
				</template>
				<template v-else>
					<n-empty description="No items found" v-if="!loading" />
				</template>
			</div>
		</n-spin>
	</div>
</template>

<script setup lang="ts">
import { ref, onBeforeMount, toRefs, computed } from "vue"
import { useMessage, NSpin, NPopover, NButton, NEmpty, NSelect, NInput } from "naive-ui"
import Api from "@/api"
import Icon from "@/components/common/Icon.vue"
import CollectItem from "./CollectItem.vue"
import type { Agent } from "@/types/agents.d"
import type { CollectRequest } from "@/api/artifacts"
import type { Artifact, CollectResult } from "@/types/artifacts.d"
import { collectResult } from "./mock"

const props = defineProps<{ agentHostname?: string }>()
const { agentHostname } = toRefs(props)

const message = useMessage()
const loadingAgents = ref(false)
const loadingArtifacts = ref(false)
const loading = ref(false)
const agents = ref<Agent[]>([])
const artifacts = ref<Artifact[]>([])
const collectList = ref<CollectResult[]>([])

const InfoIcon = "carbon:information"

const total = computed<number>(() => {
	return collectList.value.length || 0
})

const filters = ref<Partial<CollectRequest>>({})

const isFilterPreselected = computed(() => {
	return !!agentHostname?.value
})

const areFiltersValid = computed(() => {
	return !!filters.value.artifact_name && !!filters.value.hostname
})

const agentHostnameOptions = computed(() => {
	if (agentHostname?.value) {
		return [{ value: agentHostname.value, label: agentHostname.value }]
	}
	return (agents.value || []).map(o => ({ value: o.hostname, label: o.hostname }))
})

const artifactsOptions = computed(() => {
	return (artifacts.value || []).map(o => ({ value: o.name, label: o.name }))
})

function getData() {
	if (areFiltersValid.value) {
		loading.value = true

		Api.artifacts
			.collect(filters.value as CollectRequest)
			.then(res => {
				if (res.data.success) {
					collectList.value = res.data?.results || []
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

function getAgents() {
	loadingAgents.value = true

	Api.agents
		.getAgents()
		.then(res => {
			if (res.data.success) {
				agents.value = res.data.agents || []
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

function getArtifacts() {
	loadingArtifacts.value = true

	Api.artifacts
		.getAll()
		.then(res => {
			if (res.data.success) {
				artifacts.value = res.data.artifacts || []
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
	if (agentHostname?.value) {
		filters.value.hostname = agentHostname.value
	}

	getAgents()
	getArtifacts()

	// MOCK
	collectList.value = collectResult as CollectResult[]
})
</script>

<style lang="scss" scoped>
.artifacts-collect {
	:deep() {
		.n-spin-body {
			top: 100px;
			text-align: center;
			width: 80%;
		}
	}

	.list {
		container-type: inline-size;
		min-height: 200px;

		.collect-item {
			flex: 1 0 390px;
			animation: artifacts-fade 0.3s forwards;
			opacity: 0;

			@for $i from 0 through 30 {
				&:nth-child(#{$i}) {
					animation-delay: $i * 0.05s;
				}
			}

			@keyframes artifacts-fade {
				from {
					opacity: 0;
					transform: translateY(10px);
				}
				to {
					opacity: 1;
				}
			}
		}
	}
}
</style>
