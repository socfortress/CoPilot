<template>
	<div class="artifacts-list">
		<div class="header flex items-center justify-end gap-2" ref="header">
			<div class="info grow flex gap-5">
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
			<n-popover
				:show="showFilters"
				trigger="manual"
				overlap
				placement="right"
				style="padding-left: 0; padding-right: 0"
			>
				<template #trigger>
					<div class="bg-color border-radius">
						<n-button size="small" v-show="!isFilterPreselected" @click="showFilters = true">
							<template #icon>
								<Icon :name="FilterIcon"></Icon>
							</template>
						</n-button>
					</div>
				</template>
				<div class="py-1 flex flex-col gap-2">
					<div class="px-3">
						<n-input-group class="artifacts-list-filter-combo" :class="{ 'filters-active': filterType }">
							<n-select
								class="artifacts-list-filter-type"
								v-model:value="filterType"
								@update:value="
									() => {
										filters.hostname = undefined
										filters.os = undefined
									}
								"
								:options="[
									{
										label: 'Filter by Agent ',
										value: 'agentHostname'
									},
									{
										label: 'Filter by OS',
										value: 'os'
									}
								]"
								placeholder="Filters..."
								clearable
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
					<div class="px-3 flex justify-end gap-2">
						<n-button size="small" @click="showFilters = false" secondary>Close</n-button>
						<n-button size="small" @click="getData()" type="primary" secondary>Submit</n-button>
					</div>
				</div>
			</n-popover>
		</div>
		<n-spin :show="loading">
			<div class="list my-3">
				<template v-if="artifactsList.length">
					<ArtifactItem
						v-for="artifact of itemsPaginated"
						:key="artifact.name"
						:artifact="artifact"
						class="mb-2"
					/>
				</template>
				<template v-else>
					<n-empty description="No items found" v-if="!loading" />
				</template>
			</div>
		</n-spin>
		<div class="footer flex justify-end">
			<n-pagination
				v-model:page="currentPage"
				:page-size="pageSize"
				:item-count="totalArtifacts"
				:page-slot="6"
				v-if="itemsPaginated.length > 3"
			/>
		</div>
	</div>
</template>

<script setup lang="ts">
import { ref, onBeforeMount, toRefs, computed } from "vue"
import { useMessage, NSpin, NPopover, NButton, NEmpty, NSelect, NPagination, NInputGroup } from "naive-ui"
import Api from "@/api"
import Icon from "@/components/common/Icon.vue"
import ArtifactItem from "./ArtifactItem.vue"
import type { Agent } from "@/types/agents.d"
import type { ArtifactsQuery } from "@/api/artifacts"
import type { Artifact } from "@/types/artifacts.d"
import { useResizeObserver } from "@vueuse/core"

const props = defineProps<{ agentHostname?: string }>()
const { agentHostname } = toRefs(props)

const message = useMessage()
const loadingAgents = ref(false)
const loading = ref(false)
const showFilters = ref(false)
const agents = ref<Agent[]>([])
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

const filterType = ref<string | null>(null)

const isFilterPreselected = computed(() => {
	return !!agentHostname?.value
})

const agentHostnameOptions = computed(() => {
	if (agentHostname?.value) {
		return [{ value: agentHostname.value, label: agentHostname.value }]
	}
	return (agents.value || []).map(o => ({ value: o.hostname, label: o.hostname }))
})

const osOptions = [
	{ label: "Windows", value: "windows" },
	{ label: "Linux", value: "linux" },
	{ label: "MacOS", value: "macos" }
]

function getData() {
	loading.value = true

	Api.artifacts
		.getAll(filters.value)
		.then(res => {
			if (res.data.success) {
				artifactsList.value = res.data?.artifacts || []
			} else {
				message.warning(res.data?.message || "An error occurred. Please try again later.")
			}
		})
		.catch(err => {
			artifactsList.value = []

			message.error(err.response?.data?.message || "An error occurred. Please try again later.")
		})
		.finally(() => {
			loading.value = false
		})
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

	getAgents()
	getData()
})
</script>

<style lang="scss" scoped>
.artifacts-list {
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

		.artifact-item {
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

<style lang="scss">
.artifacts-list-filter-combo {
	&.filters-active {
		min-width: 290px;
		width: 50vw;
		max-width: 400px;
	}
	.artifacts-list-filter-type {
		min-width: 150px;
		max-width: 150px;
	}
}
</style>
