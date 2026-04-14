<template>
	<div>
		<div class="flex flex-col gap-4">
			<div class="flex w-full items-center justify-between gap-4">
				<Filters v-model:value="filters" class="w-auto!" @loaded="handleFiltersLoaded" />
				<CreateCaseButton secondary @success="handleCreated" />
			</div>

			<div class="flex flex-col gap-2">
				<div ref="headerRef" class="flex items-center justify-between">
					<Chip size="small" :value="loading ? 'Loading...' : pagination.total" label="items" />

					<div class="flex items-center gap-2 whitespace-nowrap">
						<n-pagination
							v-model:page="pagination.page"
							v-model:page-size="pagination.pageSize"
							:page-slot
							:show-size-picker
							:page-sizes
							:item-count="pagination.total"
							:simple="simpleMode"
							size="small"
						/>
					</div>
				</div>

				<div class="grow overflow-hidden">
					<n-data-table
						bordered
						:loading
						size="small"
						:data
						:columns
						:scroll-x="1400"
						class="[&_.n-data-table-th\_\_title]:whitespace-nowrap"
					>
						<template #empty>
							<n-empty description="No cases found">
								<template #extra>try changing the filters</template>
							</n-empty>
						</template>
					</n-data-table>
				</div>

				<div class="flex justify-end">
					<n-pagination
						v-if="pagination.total > pagination.pageSize"
						v-model:page="pagination.page"
						:page-size="pagination.pageSize"
						:item-count="pagination.total"
						:page-slot="6"
						size="small"
						:simple="simpleMode"
					/>
				</div>
			</div>
		</div>
	</div>
</template>

<script setup lang="tsx">
import type { AxiosResponse } from "axios"
import type { DataTableColumns } from "naive-ui"
import type { CaseAssignedUpdateSuccessPayload } from "@/components/cases/CaseAssignedSelect.vue"
import type { CaseStatusUpdateSuccessPayload } from "@/components/cases/CaseStatusSelect.vue"
import type { FiltersModel } from "@/components/cases/Filters.vue"
import type { Case, CasesListResponse, CaseStatus } from "@/types/cases"
import type { ApiError, CommonResponse, Pagination } from "@/types/common"
import { useDebounceFn, useElementSize } from "@vueuse/core"
import axios from "axios"
import { NDataTable, NEmpty, NPagination, NTag, useMessage } from "naive-ui"
import { computed, ref, useTemplateRef, watch } from "vue"
import Api from "@/api"
import CaseAssignedSelect from "@/components/cases/CaseAssignedSelect.vue"
import CaseDetailsButton from "@/components/cases/CaseDetailsButton.vue"
import CaseStatusSelect from "@/components/cases/CaseStatusSelect.vue"
import CreateCaseButton from "@/components/cases/CreateCaseButton.vue"
import Filters from "@/components/cases/Filters.vue"
import Chip from "@/components/common/Chip.vue"
import Icon from "@/components/common/Icon.vue"
import { useSettingsStore } from "@/stores/settings"
import { getApiErrorMessage, getStatusColor } from "@/utils"
import { formatDate } from "@/utils/format"

const message = useMessage()
const data = ref<Case[]>([])
const loading = ref(false)
const dFormats = useSettingsStore().dateFormat

const { width: headerWidthRef } = useElementSize(useTemplateRef("headerRef"))
const pageSizes = [10, 25, 50, 100]
const pageSlot = computed(() => (headerWidthRef.value < 800 ? 5 : 8))
const simpleMode = computed(() => headerWidthRef.value < 600)
const showSizePicker = ref(true)
const assignedAvailable = ref<string[]>([])

const pagination = ref({
	page: 1,
	pageSize: pageSizes[1],
	total: 0
})

// Filters
const filters = ref<FiltersModel>({
	key: null,
	value: null
})

const columns = computed<DataTableColumns<Case>>(() => [
	{
		title: "Case Name",
		key: "case_name",
		fixed: simpleMode.value ? undefined : "left",
		width: 380,
		render: row => <div>{row.case_name}</div>
	},
	{
		title: "Created",
		key: "case_creation_time",
		width: "100%",
		minWidth: 200,
		render: row => <span class="font-mono text-sm">{formatDate(row.case_creation_time, dFormats.datetime)}</span>
	},
	{
		title: "Assigned To",
		key: "assigned_to",
		width: 120,
		render: row => {
			return (
				<CaseAssignedSelect
					caseId={row.id}
					assignedTo={row.assigned_to}
					assignedAvailable={assignedAvailable.value}
					onSuccess={handleAssignedToUpdateSuccess}
				/>
			)
		}
	},
	{
		title: "Status",
		key: "status",
		width: 120,
		render: row => {
			return (
				<div class="flex items-center gap-2">
					<NTag
						type={getStatusColor(row.case_status)}
						round
						class="p-1! [&_.n-tag\_\_icon]:m-0!"
						v-slots={{
							icon: () => <Icon name="carbon:circle-solid" />
						}}
					/>
					<CaseStatusSelect caseId={row.id} status={row.case_status} onSuccess={handleStatusUpdateSuccess} />
				</div>
			)
		}
	},
	{
		title: "Actions",
		key: "actions",
		minWidth: 180,
		render: row => {
			return (
				<CaseDetailsButton
					caseId={row.id}
					onStatusUpdated={handleStatusUpdateSuccess}
					onAssignedToUpdated={handleAssignedToUpdateSuccess}
					onDeleted={handleDeleted}
				/>
			)
		}
	}
])

let abortController = new AbortController()

const loadCases = useDebounceFn(async () => {
	loading.value = true

	abortController?.abort()
	abortController = new AbortController()

	try {
		let response: AxiosResponse<CommonResponse<CasesListResponse>>

		const paginationPayload: Pagination = {
			page: pagination.value.page,
			pageSize: pagination.value.pageSize,
			order: "desc"
		}

		if (filters.value.key && filters.value.value) {
			switch (filters.value.key) {
				case "statuses":
					response = await Api.cases.getCasesByStatus(
						filters.value.value as CaseStatus,
						paginationPayload,
						abortController.signal
					)
					break
				case "assigned_to":
					response = await Api.cases.getCasesByAssignedTo(
						filters.value.value,
						paginationPayload,
						abortController.signal
					)
					break
				default:
					response = await Api.cases.getCases(paginationPayload, abortController.signal)
					break
			}
		} else {
			response = await Api.cases.getCases(paginationPayload, abortController.signal)
		}

		data.value = response.data.cases
		pagination.value.total = response.data.total
		loading.value = false
	} catch (err) {
		if (!axios.isCancel(err)) {
			message.error(getApiErrorMessage(err as ApiError))
			loading.value = false
		}
	}
}, 400)

function resetPage() {
	pagination.value.page = 1
	loadCases()
}

function handleFiltersLoaded(value: Record<string, string[]>) {
	assignedAvailable.value = value.assigned_to || []
}

function handleDeleted() {
	loadCases()
}

function resetFilters() {
	filters.value.key = null
	filters.value.value = null
}

function resetPagination() {
	pagination.value.page = 1
	pagination.value.pageSize = pageSizes[1]
}

function handleCreated() {
	resetFilters()
	resetPagination()
	loadCases()
}

function handleAssignedToUpdateSuccess(payload: CaseAssignedUpdateSuccessPayload) {
	const case_ = data.value.find(c => c.id === payload.caseId)
	if (case_) {
		case_.assigned_to = payload.assignedTo
	}
}

function handleStatusUpdateSuccess(payload: CaseStatusUpdateSuccessPayload) {
	const case_ = data.value.find(c => c.id === payload.caseId)
	if (case_) {
		case_.case_status = payload.status
	}
}

watch([() => pagination.value.pageSize, () => filters.value.value], resetPage, {
	deep: true,
	immediate: true
})

watch(() => pagination.value.page, loadCases, {
	deep: true,
	immediate: true
})
</script>
