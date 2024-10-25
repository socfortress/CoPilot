<template>
	<div class="sigma-queries-list">
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
							<code>{{ total }}</code>
						</div>
						<div class="box">
							<span class="text-success">Active</span>
							:
							<code>{{ activeTotal }}</code>
						</div>
						<div class="box">
							<span class="text-secondary">Inactive</span>
							:
							<code>{{ inactiveTotal }}</code>
						</div>
					</div>
				</n-popover>

				<n-button size="small" type="primary" secondary strong @click="showActionsView = !showActionsView">
					<div class="flex items-center gap-2">
						<Icon :name="ToolsIcon" :size="16"></Icon>
						<span class="xs:block hidden">Actions</span>
						<Icon
							class="xs:!block !hidden transition-transform"
							:class="{ '!rotate-90': showActionsView }"
							:name="ChevronIcon"
							:size="16"
						></Icon>
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
					<div class="bg-default rounded-default">
						<n-badge :show="filtered" dot type="success" :offset="[-4, 0]">
							<n-button size="small" @click="showFilters = true">
								<template #icon>
									<Icon :name="FilterIcon"></Icon>
								</template>
							</n-button>
						</n-badge>
					</div>
				</template>
				<div class="flex flex-col gap-2 py-1">
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
					<div class="flex justify-between gap-2 px-3">
						<div class="flex justify-start gap-2">
							<n-button size="small" quaternary @click="showFilters = false">Close</n-button>
						</div>
						<div class="flex justify-end gap-2">
							<n-button size="small" secondary @click="resetFilters()">Reset</n-button>
							<n-button size="small" type="primary" secondary :loading @click="getData()">
								Submit
							</n-button>
						</div>
					</div>
				</div>
			</n-popover>
		</div>

		<div class="actions-box" :class="{ open: showActionsView }">
			<n-card size="small" content-class="bg-secondary" class="overflow-hidden" :bordered="false">
				<QueriesActions @updated="getData()" />
			</n-card>
		</div>

		<n-spin :show="loading">
			<div class="list my-3 flex flex-col gap-2">
				<template v-if="queriesList.length">
					<QueryItem
						v-for="query of itemsPaginated"
						:key="query.id"
						:query="query"
						class="item-appear item-appear-bottom item-appear-005"
						@deleted="deleteQueryItem"
						@updated="updateQueryItem"
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
				:item-count="total"
				:page-slot="6"
			/>
		</div>
	</div>
</template>

<script setup lang="ts">
import type { SigmaQuery } from "@/types/sigma.d"
import Api from "@/api"
import Icon from "@/components/common/Icon.vue"
import { useResizeObserver, useStorage } from "@vueuse/core"
import _cloneDeep from "lodash/cloneDeep"
import _orderBy from "lodash/orderBy"
import { NBadge, NButton, NCard, NEmpty, NPagination, NPopover, NSelect, NSpin, useMessage } from "naive-ui"
import { computed, onBeforeMount, ref, watch } from "vue"
import QueriesActions from "./QueriesActions.vue"
import QueryItem from "./QueryItem.vue"

interface QueriesFilter {
	active: "active" | "inactive"
}

const FilterIcon = "carbon:filter-edit"
const InfoIcon = "carbon:information"
const ToolsIcon = "carbon:tools"
const ChevronIcon = "carbon:chevron-right"

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
		position: relative;
		transition:
			opacity var(--router-transition-duration) ease-out,
			grid-template-rows var(--router-transition-duration) ease-out,
			padding-top var(--router-transition-duration) ease-out;

		&::after {
			--size: 10px;
			content: "";
			width: 0;
			height: 0;
			border-left: var(--size) solid transparent;
			border-right: var(--size) solid transparent;
			border-bottom: var(--size) solid var(--bg-secondary-color);
			position: absolute;
			top: 2px;
			left: 54px;
			transform: rotateX(90deg);
			transform-origin: top center;
			transition:
				opacity var(--router-transition-duration) ease-out,
				transform var(--router-transition-duration) ease-out;
		}

		&.open {
			grid-template-rows: 1fr;
			opacity: 1;
			@apply pt-3;

			&::after {
				transform: rotateX(0deg);
			}
		}
	}
}
</style>
