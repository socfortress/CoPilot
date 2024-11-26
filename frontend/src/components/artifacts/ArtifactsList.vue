<template>
	<div class="artifacts-list">
		<div ref="header" class="header flex items-center justify-end gap-2">
			<div class="info flex grow gap-2">
				<n-popover overlap placement="bottom-start">
					<template #trigger>
						<div class="bg-default rounded-default">
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
							<code>{{ totalArtifacts }}</code>
						</div>
					</div>
				</n-popover>
			</div>
			<n-pagination
				v-model:page="currentPage"
				v-model:page-size="pageSize"
				:page-slot="pageSlot"
				:show-size-picker="showSizePicker"
				:page-sizes="pageSizes"
				:item-count="totalArtifacts"
				:simple="simpleMode"
			/>
			<n-popover :show="showFilters" trigger="manual" overlap placement="right" class="!px-0">
				<template #trigger>
					<div class="bg-default rounded-default">
						<n-badge
							:show="!!lastFilters.hostname || !!lastFilters.os"
							dot
							type="success"
							:offset="[-4, 0]"
						>
							<n-button v-show="!isFilterPreselected" size="small" @click="(showFilters = true)">
								<template #icon>
									<Icon :name="FilterIcon"></Icon>
								</template>
							</n-button>
						</n-badge>
					</div>
				</template>
				<div class="flex flex-col gap-2 py-1">
					<div class="px-3">
						<n-input-group class="artifacts-list-filter-combo" :class="{ 'filters-active': filterType }">
							<n-select
								v-model:value="filterType"
								class="artifacts-list-filter-type"
								:options="[
									{
										label: 'Agent ',
										value: 'agentHostname'
									},
									{
										label: 'OS',
										value: 'os'
									}
								]"
								placeholder="Filters..."
								clearable
								@update:value="
									() => {
										filters.hostname = undefined
										filters.os = undefined
									}
								"
							/>

							<n-select
								v-if="filterType === 'agentHostname'"
								v-model:value="filters.hostname"
								:options="agentHostnameOptions"
								placeholder="Select Agent"
								clearable
								filterable
								:loading="loadingAgents"
							/>
							<n-select
								v-if="filterType === 'os'"
								v-model:value="filters.os"
								:options="osOptions"
								clearable
								placeholder="Select OS"
							/>
						</n-input-group>
					</div>
					<div class="flex justify-end gap-2 px-3">
						<n-button size="small" secondary @click="(showFilters = false)">Close</n-button>
						<n-button size="small" type="primary" secondary @click="getData()">Submit</n-button>
					</div>
				</div>
			</n-popover>
		</div>
		<n-spin :show="loading">
			<div class="my-3 flex min-h-52 flex-col gap-2">
				<template v-if="artifactsList.length">
					<ArtifactItem
						v-for="artifact of itemsPaginated"
						:key="artifact.name"
						:artifact="artifact"
						class="item-appear item-appear-bottom item-appear-005"
					/>
				</template>
				<template v-else>
					<n-empty v-if="!loading" description="No items found" class="h-48 justify-center" />
				</template>
			</div>
		</n-spin>
		<div class="footer flex justify-end">
			<n-pagination
				v-if="itemsPaginated.length > 3"
				v-model:page="currentPage"
				:page-size="pageSize"
				:item-count="totalArtifacts"
				:page-slot="6"
			/>
		</div>
	</div>
</template>

<script setup lang="ts">
import type { ArtifactsQuery } from "@/api/endpoints/artifacts"
import type { Agent } from "@/types/agents.d"
import type { Artifact } from "@/types/artifacts.d"
import Api from "@/api"
import Icon from "@/components/common/Icon.vue"
import { useResizeObserver } from "@vueuse/core"
import _cloneDeep from "lodash/cloneDeep"
import { NBadge, NButton, NEmpty, NInputGroup, NPagination, NPopover, NSelect, NSpin, useMessage } from "naive-ui"
import { computed, nextTick, onBeforeMount, ref, toRefs, watch } from "vue"
import ArtifactItem from "./ArtifactItem.vue"

const props = defineProps<{ agentHostname?: string; agents?: Agent[]; artifacts?: Artifact[] }>()

const emit = defineEmits<{
	(e: "loaded-agents", value: Agent[]): void
	(e: "loaded-artifacts", value: Artifact[]): void
}>()

const { agentHostname, agents, artifacts } = toRefs(props)

const message = useMessage()
const loadingAgents = ref(false)
const loading = ref(false)
const showFilters = ref(false)
const agentsList = ref<Agent[]>([])
const artifactsList = ref<Artifact[]>([])

const pageSize = ref(25)
const currentPage = ref(1)
const simpleMode = ref(false)
const showSizePicker = ref(true)
const pageSizes = [10, 25, 50, 100]
const header = ref()
const pageSlot = ref(8)

const itemsPaginated = computed(() => {
	const from = (currentPage.value - 1) * pageSize.value
	const to = currentPage.value * pageSize.value

	return artifactsList.value.slice(from, to)
})

const FilterIcon = "carbon:filter-edit"
const InfoIcon = "carbon:information"

const totalArtifacts = computed<number>(() => {
	return artifactsList.value.length || 0
})

const filters = ref<ArtifactsQuery>({})
const lastFilters = ref<ArtifactsQuery>({})

const filterType = ref<string | null>(null)

const isFilterPreselected = computed(() => {
	return !!agentHostname?.value
})

const agentHostnameOptions = computed(() => {
	if (agentHostname?.value) {
		return [{ value: agentHostname.value, label: agentHostname.value }]
	}
	return (agentsList.value || []).map(o => ({ value: o.hostname, label: o.hostname }))
})

const osOptions = [
	{ label: "Windows", value: "windows" },
	{ label: "Linux", value: "linux" },
	{ label: "MacOS", value: "macos" }
]

watch(showFilters, val => {
	if (!val) {
		filters.value = _cloneDeep(lastFilters.value)
	}
})

function getData(cb?: (artifacts: Artifact[]) => void) {
	showFilters.value = false
	loading.value = true

	lastFilters.value = _cloneDeep(filters.value)

	Api.artifacts
		.getAll(filters.value)
		.then(res => {
			if (res.data.success) {
				artifactsList.value = res.data?.artifacts || []

				if (cb && typeof cb === "function") {
					cb(artifactsList.value)
				}
			} else {
				message.warning(res.data?.message || "An error occurred. Please try again later.")
			}
		})
		.catch(err => {
			artifactsList.value = []

			// MOCK
			/*
			artifactsList.value = artifact_list
			*/

			message.error(err.response?.data?.message || "An error occurred. Please try again later.")
		})
		.finally(() => {
			loading.value = false
		})
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

useResizeObserver(header, entries => {
	const entry = entries[0]
	const { width } = entry.contentRect

	pageSlot.value = width < 650 ? 5 : 8
	simpleMode.value = width < 450
})

onBeforeMount(() => {
	if (agentHostname?.value) {
		filters.value.hostname = agentHostname.value
	}

	if (agents?.value?.length) {
		agentsList.value = agents.value
	}

	if (artifacts?.value?.length) {
		artifactsList.value = artifacts.value
	}

	nextTick(() => {
		if (!agentsList.value.length && !agentHostname?.value) {
			getAgents((agents: Agent[]) => {
				emit("loaded-agents", agents)
			})
		}
		if (!artifactsList.value.length) {
			getData((artifacts: Artifact[]) => {
				emit("loaded-artifacts", artifacts)
			})
		}
	})
})
</script>

<style lang="scss">
.artifacts-list-filter-combo {
	.artifacts-list-filter-type {
		min-width: 130px;
		max-width: 130px;
	}

	&.filters-active {
		min-width: 270px;
		width: 50vw;
		max-width: 400px;

		.artifacts-list-filter-type {
			min-width: 100px;
			max-width: 100px;
		}
	}
}
</style>
