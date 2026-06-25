<template>
	<div class="audit-list">
		<div ref="header" class="header flex items-center justify-end gap-2">
			<div class="info flex grow gap-2">
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
							Total matching :
							<code>{{ total }}</code>
						</div>
					</div>
				</n-popover>
			</div>

			<n-pagination
				v-model:page="currentPage"
				v-model:page-size="pageSize"
				:page-slot
				:show-size-picker
				:page-sizes
				:item-count="total"
				:simple="simpleMode"
				@update:page="getData()"
				@update:page-size="onPageSizeChange()"
			/>

			<n-popover :show="showFilters" trigger="manual" placement="bottom-end" class="px-0!" to="body">
				<template #trigger>
					<div class="bg-default rounded-lg">
						<n-badge :show="filtered" dot type="success" :offset="[-4, 0]">
							<n-button size="small" @click="showFilters = true">
								<template #icon>
									<Icon :name="FilterIcon" />
								</template>
							</n-button>
						</n-badge>
					</div>
				</template>
				<AuditFilters
					v-model:filters="filters"
					:actions
					:results
					@submit="applyFilters()"
					@close="showFilters = false"
				/>
			</n-popover>
		</div>

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
				@update:page="getData()"
			/>
		</div>
	</div>
</template>

<script setup lang="ts">
import type { AuditLogEntry, AuditLogFilters, AuditUiFilters } from "@/types/audit.d"
import type { ApiError } from "@/types/common"
import { useResizeObserver } from "@vueuse/core"
import { NBadge, NButton, NEmpty, NPagination, NPopover, NSpin, useMessage } from "naive-ui"
import { computed, onBeforeMount, ref } from "vue"
import Api from "@/api"
import Icon from "@/components/common/Icon.vue"
import { getApiErrorMessage } from "@/utils"
import AuditFilters from "./AuditFilters.vue"
import AuditItem from "./AuditItem.vue"

const message = useMessage()

const loading = ref(false)
const list = ref<AuditLogEntry[]>([])
const total = ref(0)
const showFilters = ref(false)

const actions = ref<string[]>([])
const results = ref<string[]>([])

const pageSize = ref(25)
const currentPage = ref(1)
const simpleMode = ref(false)
const showSizePicker = ref(true)
const pageSizes = [10, 25, 50, 100]
const header = ref()
const pageSlot = ref(8)

const FilterIcon = "carbon:filter-edit"
const InfoIcon = "carbon:information"

const filters = ref<AuditUiFilters>({
	action: null,
	result: null,
	entity_type: null,
	actor_username: null,
	customer_code: null,
	search: null,
	dateRange: null
})

const filtered = computed(() => {
	const f = filters.value
	return Boolean(
		f.action || f.result || f.entity_type || f.actor_username || f.customer_code || f.search || f.dateRange
	)
})

function buildApiFilters(): AuditLogFilters {
	const f = filters.value
	const api: AuditLogFilters = {
		skip: (currentPage.value - 1) * pageSize.value,
		limit: pageSize.value
	}
	if (f.action) api.action = f.action
	if (f.result) api.result = f.result
	if (f.entity_type) api.entity_type = f.entity_type
	if (f.actor_username) api.actor_username = f.actor_username
	if (f.customer_code) api.customer_code = f.customer_code
	if (f.search) api.search = f.search
	if (f.dateRange) {
		api.start_time = new Date(f.dateRange[0]).toISOString()
		api.end_time = new Date(f.dateRange[1]).toISOString()
	}
	return api
}

function getData() {
	loading.value = true

	Api.audit
		.getAuditLogs(buildApiFilters())
		.then(res => {
			if (res.data.success) {
				list.value = res.data.audit_logs || []
				total.value = res.data.pagination?.total ?? 0
			} else {
				message.warning(res.data?.message || "An error occurred. Please try again later.")
			}
		})
		.catch(err => {
			list.value = []
			message.error(getApiErrorMessage(err as ApiError) || "An error occurred. Please try again later.")
		})
		.finally(() => {
			loading.value = false
		})
}

function applyFilters() {
	showFilters.value = false
	currentPage.value = 1
	getData()
}

function onPageSizeChange() {
	currentPage.value = 1
	getData()
}

function getVocabularies() {
	Api.audit
		.getAuditVocabularies()
		.then(res => {
			if (res.data.success) {
				actions.value = res.data.actions || []
				results.value = res.data.results || []
			}
		})
		.catch(() => {
			// Non-fatal: filter dropdowns simply stay empty.
		})
}

useResizeObserver(header, entries => {
	const entry = entries[0]
	if (!entry) return

	const { width } = entry.contentRect

	pageSlot.value = width < 700 ? 5 : 8
	simpleMode.value = width < 550
})

onBeforeMount(() => {
	getVocabularies()
	getData()
})
</script>
