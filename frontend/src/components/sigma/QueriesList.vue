<template>
	<div class="sigma-queries-list">
		<div class="header flex items-center justify-end gap-2" ref="header">
			<div class="info grow flex gap-2">
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
						<div class="box">
							<span class="text-success-color">Active</span>
							:
							<code>{{ activeTotal }}</code>
						</div>
						<div class="box">
							<span class="text-secondary-color">Inactive</span>
							:
							<code>{{ inactiveTotal }}</code>
						</div>
					</div>
				</n-popover>

				<n-button size="small" type="primary" secondary strong @click="showActionsView = !showActionsView">
					<div class="flex items-center gap-2">
						<Icon :name="ToolsIcon" :size="16"></Icon>
						<span class="hidden xs:block">Actions</span>
					</div>
				</n-button>
			</div>
			<n-pagination
				v-model:page="currentPage"
				v-model:page-size="pageSize"
				:page-slot="pageSlot"
				:show-size-picker="showSizePicker"
				:page-sizes="pageSizes"
				:item-count="total"
				:simple="simpleMode"
			/>
			<n-popover :show="showFilters" trigger="manual" overlap placement="right" class="!px-0">
				<template #trigger>
					<div class="bg-color border-radius">
						<n-badge :show="filtered" dot type="success" :offset="[-4, 0]">
							<n-button size="small" @click="showFilters = true">
								<template #icon>
									<Icon :name="FilterIcon"></Icon>
								</template>
							</n-button>
						</n-badge>
					</div>
				</template>
				<div class="py-1 flex flex-col gap-2">
					<div class="px-3">
						<small>Status:</small>
					</div>
					<div class="px-3">
						<n-select
							v-model:value="filters.active"
							:options="activeOptions"
							placeholder="Active Status"
							clearable
							class="!w-56"
						/>
					</div>
					<div class="px-3 flex justify-between gap-2">
						<div class="flex justify-start gap-2">
							<n-button size="small" @click="showFilters = false" quaternary>Close</n-button>
						</div>
						<div class="flex justify-end gap-2">
							<n-button size="small" @click="resetFilters()" secondary>Reset</n-button>
							<n-button size="small" @click="getData()" type="primary" secondary :loading>
								Submit
							</n-button>
						</div>
					</div>
				</div>
			</n-popover>
		</div>

		<div class="actions-box" :class="{ open: showActionsView }">
			<n-card size="small" content-class="bg-secondary-color" class="overflow-hidden" :bordered="false">
				<QueriesActions @updated="getData()" />
			</n-card>
		</div>

		<n-spin :show="loading">
			<div class="list flex flex-col gap-2 my-3">
				<template v-if="queriesList.length">
					<QueryItem
						v-for="query of itemsPaginated"
						:key="query.id"
						:query="query"
						@deleted="deleteQueryItem"
						@updated="updateQueryItem"
						class="item-appear item-appear-bottom item-appear-005"
					/>
				</template>
				<template v-else>
					<n-empty description="No items found" class="justify-center h-48" v-if="!loading" />
				</template>
			</div>
		</n-spin>

		<div class="footer flex justify-end">
			<n-pagination
				v-model:page="currentPage"
				:page-size="pageSize"
				:item-count="total"
				:page-slot="6"
				v-if="itemsPaginated.length > 3"
			/>
		</div>
	</div>
</template>

<script setup lang="ts">
import { ref, onBeforeMount, computed, watch } from "vue"
import { NCard, NSpin, NPopover, NButton, NEmpty, NSelect, NPagination, NBadge, useMessage } from "naive-ui"
import Api from "@/api"
import _cloneDeep from "lodash/cloneDeep"
import _orderBy from "lodash/orderBy"
import Icon from "@/components/common/Icon.vue"
import { useResizeObserver, useStorage } from "@vueuse/core"
import QueryItem from "./QueryItem.vue"
import QueriesActions from "./QueriesActions.vue"
import type { SigmaQuery } from "@/types/sigma.d"

interface QueriesFilter {
	active: "active" | "inactive"
}

const FilterIcon = "carbon:filter-edit"
const InfoIcon = "carbon:information"
const ToolsIcon = "carbon:tools"

const message = useMessage()
const loading = ref(false)
const showFilters = ref(false)
const showActionsView = useStorage<boolean>("sigma-queries-list-actions-view-state", false, localStorage)
const queriesList = ref<SigmaQuery[]>([])

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

	const list = _orderBy(queriesList.value, ["id"], ["desc"])

	return list.slice(from, to)
})

const total = computed<number>(() => {
	return queriesList.value.length || 0
})
const activeTotal = computed<number>(() => {
	return queriesList.value.filter(o => o.active).length || 0
})
const inactiveTotal = computed<number>(() => {
	return queriesList.value.filter(o => !o.active).length || 0
})

const filters = ref<Partial<QueriesFilter>>({})
const lastFilters = ref<Partial<QueriesFilter>>({})

const filtered = computed<boolean>(() => {
	return !!filters.value.active
})

const activeOptions = [
	{ label: "Active", value: "active" },
	{ label: "Inactive", value: "inactive" }
]

watch(showFilters, val => {
	if (!val) {
		filters.value = _cloneDeep(lastFilters.value)
	}
})

function updateQueryItem(query: SigmaQuery) {
	const index = queriesList.value.findIndex(o => o.id === query.id)
	if (index !== -1) {
		queriesList.value[index] = query
	}
}

function deleteQueryItem(query: SigmaQuery) {
	const index = queriesList.value.findIndex(o => o.id === query.id)
	queriesList.value.splice(index, 1)
}

function resetFilters() {
	filters.value.active = undefined
	showFilters.value = false
	getData()
}

function getData() {
	showFilters.value = false
	loading.value = true

	lastFilters.value = _cloneDeep(filters.value)

	const method = !filtered.value ? "getAvailable" : filters.value.active === "active" ? "getActive" : "getInactive"

	Api.sigma[method]()
		.then(res => {
			if (res.data.success) {
				queriesList.value = res.data?.sigma_queries || []
			} else {
				message.warning(res.data?.message || "An error occurred. Please try again later.")
			}
		})
		.catch(err => {
			queriesList.value = []

			message.error(err.response?.data?.message || "An error occurred. Please try again later.")
		})
		.finally(() => {
			loading.value = false
		})
}

useResizeObserver(header, entries => {
	const entry = entries[0]
	const { width } = entry.contentRect

	pageSlot.value = width < 700 ? 5 : 8
	simpleMode.value = width < 550
})

onBeforeMount(() => {
	getData()
})
</script>

<style lang="scss" scoped>
.sigma-queries-list {
	.list {
		container-type: inline-size;
		min-height: 200px;
	}

	.actions-box {
		overflow: hidden;
		display: grid;
		grid-template-rows: 0fr;
		padding-top: 0px;
		opacity: 0;
		transition:
			opacity var(--router-transition-duration) ease-out,
			grid-template-rows var(--router-transition-duration) ease-out,
			padding-top var(--router-transition-duration) ease-out;

		&.open {
			grid-template-rows: 1fr;
			opacity: 1;
			@apply pt-3;
		}
	}
}
</style>
