<template>
	<div class="flex flex-col gap-2">
		<div ref="headerRef" class="flex items-center justify-between">
			<Chip size="small" :value="loading ? 'Loading...' : paginatedTotal" label="items" />

			<div class="flex items-center gap-2 whitespace-nowrap">
				<n-pagination
					v-model:page="pagination.page"
					v-model:page-size="pagination.pageSize"
					:page-slot
					:show-size-picker
					:page-sizes
					:item-count="paginatedTotal"
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
				:data="dataPaginated"
				:columns
				:scroll-x="1150"
				class="[&_.n-data-table-th\_\_title]:whitespace-nowrap"
			>
				<template #empty>
					<n-empty description="No dashboards enabled">
						<template #extra>Contact your administrator to enable dashboards for your account</template>
					</n-empty>
				</template>
			</n-data-table>
		</div>

		<div class="flex justify-end">
			<n-pagination
				v-if="paginatedTotal > pagination.pageSize"
				v-model:page="pagination.page"
				:page-size="pagination.pageSize"
				:item-count="paginatedTotal"
				:page-slot="6"
				size="small"
				:simple="simpleMode"
			/>
		</div>
	</div>
</template>

<script setup lang="tsx">
import type { DataTableColumns } from "naive-ui"
import type { ApiError } from "@/types/common"
import type { EnabledDashboard } from "@/types/siem"
import { useDebounceFn, useElementSize } from "@vueuse/core"
import axios from "axios"
import { NButton, NDataTable, NEmpty, NPagination, useMessage } from "naive-ui"
import { computed, onBeforeMount, ref, useTemplateRef, watch } from "vue"
import Api from "@/api"
import Chip from "@/components/common/Chip.vue"
import Icon from "@/components/common/Icon.vue"
import { useNavigation } from "@/composables/common/useNavigation"
import { useAuthStore } from "@/stores/auth"
import { useSettingsStore } from "@/stores/settings"
import { getApiErrorMessage } from "@/utils"
import { formatDate } from "@/utils/format"

const emit = defineEmits<{
	(e: "loaded", value: EnabledDashboard[]): void
	(e: "loading", value: boolean): void
}>()

const authStore = useAuthStore()
const { routeDashboardViewer } = useNavigation()
const message = useMessage()
const loading = ref(false)
const dFormats = useSettingsStore().dateFormat
const customerCode = computed(() => authStore.userCustomerCode || "")

const { width: headerWidthRef } = useElementSize(useTemplateRef("headerRef"))
const pageSizes = [10, 25, 50, 100]
const pageSlot = computed(() => (headerWidthRef.value < 800 ? 5 : 8))
const simpleMode = computed(() => headerWidthRef.value < 600)
const showSizePicker = ref(true)

const pagination = ref({
	page: 1,
	pageSize: pageSizes[1]
})

const data = ref<EnabledDashboard[]>([])

const dataPaginated = computed(() => {
	const from = (pagination.value.page - 1) * pagination.value.pageSize
	const to = pagination.value.page * pagination.value.pageSize

	return data.value.slice(from, to)
})

const paginatedTotal = computed(() => data.value.length)

const columns = computed<DataTableColumns<EnabledDashboard>>(() => [
	{
		title: "Dashboard",
		key: "display_name",
		fixed: simpleMode.value ? undefined : "left",
		width: 280,
		render: row => <div>{row.display_name}</div>
	},
	{
		title: "Category",
		key: "library_card",
		width: 230,
		render: row => <div>{row.library_card}</div>
	},
	{
		title: "Template",
		key: "template_id",
		width: "100%",
		render: row => <div>{row.template_id}</div>
	},
	{
		title: "Created",
		key: "created_at",
		width: 200,
		render: row => <div>{formatDate(row.created_at, dFormats.datetime)}</div>
	},
	{
		title: "Actions",
		key: "actions",
		minWidth: 130,
		render: row => {
			return (
				<NButton
					onClick={() => routeDashboardViewer(row.id).navigate()}
					v-slots={{
						icon: () => <Icon name="carbon:launch" />
					}}
				>
					View Dashboard
				</NButton>
			)
		}
	}
])

let abortController = new AbortController()

const loadDashboards = useDebounceFn(async () => {
	loading.value = true

	abortController?.abort()
	abortController = new AbortController()

	try {
		const response = await Api.siem.getEnabledDashboards(customerCode.value)

		data.value = response.data?.enabled_dashboards || []
		emit("loaded", data.value)
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
}

watch(
	loading,
	value => {
		emit("loading", value)
	},
	{ immediate: true }
)

watch([() => pagination.value.pageSize], resetPage, {
	deep: true,
	immediate: true
})

onBeforeMount(() => {
	loadDashboards()
})
</script>
