<template>
	<div class="audit-list @container">
		<div ref="header" class="flex items-center justify-between gap-2">
			<div class="flex grow items-center gap-2">
				<div class="flex grow gap-2 @6xl:hidden!">
					<n-popover overlap placement="left">
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
								Total matching :
								<code>{{ total }}</code>
							</div>
						</div>
					</n-popover>
				</div>
				<div class="hidden grow items-center gap-1 text-sm @6xl:flex">
					<n-button quaternary size="small">
						<div class="flex items-center gap-2">
							<span>Total matching</span>
							<code class="py-1">{{ total }}</code>
						</div>
					</n-button>
				</div>
			</div>

			<div class="flex items-center justify-end gap-2 whitespace-nowrap">
				<n-pagination
					v-model:page="currentPage"
					v-model:page-size="pageSize"
					:page-slot
					:show-size-picker
					:page-sizes
					:item-count="total"
					:simple="simpleMode"
				/>

				<n-badge v-if="showFilters" :show="filtered" dot type="success" :offset="[-4, 0]">
					<n-button size="small" secondary @click="showFiltersView = !showFiltersView">
						<template #icon>
							<Icon :name="FilterIcon" />
						</template>
					</n-button>
				</n-badge>
			</div>
		</div>

		<CollapseKeepAlive v-if="showFilters" :show="showFiltersView" embedded arrow="top-right">
			<AuditFilters :use-query-string="!preset?.length" :preset class="p-3" @submit="applyFilters" />
		</CollapseKeepAlive>

		<n-spin :show="loading">
			<div class="my-3 flex min-h-52 flex-col gap-2">
				<template v-if="list.length">
					<AuditItem
						v-for="entry of list"
						:key="entry.id"
						:entry
						class="item-appear item-appear-bottom item-appear-005"
					/>
				</template>
				<template v-else>
					<n-empty v-if="!loading" description="No audit entries found" class="h-48 justify-center" />
				</template>
			</div>
		</n-spin>

		<div class="footer flex justify-end">
			<n-pagination
				v-if="list.length > 3"
				v-model:page="currentPage"
				:page-size
				:item-count="total"
				:page-slot="6"
			/>
		</div>
	</div>
</template>

<script setup lang="ts">
import type { AuditListFilter } from "./types"
import type { AuditLogEntry, AuditLogFilters } from "@/types/audit"
import type { ApiError } from "@/types/common"
import { useResizeObserver, useStorage } from "@vueuse/core"
import axios from "axios"
import { NBadge, NButton, NEmpty, NPagination, NPopover, NSpin, useMessage } from "naive-ui"
import { computed, onBeforeMount, ref, watch } from "vue"
import Api from "@/api"
import CollapseKeepAlive from "@/components/common/CollapseKeepAlive.vue"
import Icon from "@/components/common/Icon.vue"
import { getApiErrorMessage } from "@/utils"
import AuditFilters from "./AuditFilters.vue"
import AuditItem from "./AuditItem.vue"

const { preset, showFilters = true } = defineProps<{
	preset?: AuditListFilter[]
	showFilters?: boolean
}>()

const FilterIcon = "carbon:filter-edit"
const InfoIcon = "carbon:information"

const message = useMessage()

const loading = ref(false)
const list = ref<AuditLogEntry[]>([])
const total = ref(0)
const showFiltersView = useStorage<boolean>("audit-list-filters-view-state", false, localStorage)

const pageSize = ref(25)
const currentPage = ref(1)
const simpleMode = ref(false)
const showSizePicker = ref(true)
const pageSizes = [10, 25, 50, 100]
const header = ref()
const pageSlot = ref(8)

const filters = ref<AuditListFilter[]>([])

let abortController: AbortController | null = null

const filtered = computed(() => !!filters.value.length)

function buildApiFilters(): AuditLogFilters {
	const api: AuditLogFilters = {
		skip: (currentPage.value - 1) * pageSize.value,
		limit: pageSize.value
	}

	for (const filter of filters.value) {
		if (!filter.value) continue

		switch (filter.type) {
			case "action":
				api.action = filter.value as string
				break
			case "result":
				api.result = filter.value as string
				break
			case "actor_username":
				api.actor_username = filter.value as string
				break
			case "entity_type":
				api.entity_type = filter.value as string
				break
			case "customer_code":
				api.customer_code = filter.value as string
				break
			case "search":
				api.search = filter.value as string
				break
			case "dateRange": {
				const range = filter.value as [number, number]
				api.start_time = new Date(range[0]).toISOString()
				api.end_time = new Date(range[1]).toISOString()
				break
			}
		}
	}

	return api
}

function getData() {
	abortController?.abort()
	abortController = new AbortController()

	loading.value = true

	Api.audit
		.getAuditLogs(buildApiFilters(), abortController.signal)
		.then(res => {
			if (res.data.success) {
				list.value = res.data.audit_logs || []
				total.value = res.data.pagination?.total ?? 0
			} else {
				message.warning(res.data?.message || "An error occurred. Please try again later.")
			}
			loading.value = false
		})
		.catch(err => {
			if (!axios.isCancel(err)) {
				list.value = []
				message.error(getApiErrorMessage(err as ApiError) || "An error occurred. Please try again later.")
				loading.value = false
			}
		})
}

function applyFilters(newFilters: AuditListFilter[]) {
	filters.value = newFilters
	currentPage.value = 1
	getData()
}

watch(currentPage, () => {
	getData()
})

watch(pageSize, () => {
	if (currentPage.value === 1) {
		getData()
	} else {
		currentPage.value = 1
	}
})

useResizeObserver(header, entries => {
	const entry = entries[0]
	if (!entry) return

	const { width } = entry.contentRect

	pageSlot.value = width < 700 ? 5 : 8
	simpleMode.value = width < 550
})

onBeforeMount(() => {
	if (!showFilters && preset?.length) {
		filters.value = preset
	}

	getData()
})
</script>
