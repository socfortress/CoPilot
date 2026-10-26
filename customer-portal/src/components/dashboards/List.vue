<template>
	<div class="flex flex-col gap-2">
		<div ref="headerRef" class="flex items-center justify-between">
			<Chip
				size="small"
				:value="loading ? $t('common.states.loading') : paginatedTotal"
				:label="$t('dashboards.list.items')"
			/>

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
					<n-empty :description="$t('dashboards.list.empty')">
						<template #extra>{{ $t("dashboards.list.emptyHint") }}</template>
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
import { useElementSize } from "@vueuse/core"
import { NButton, NDataTable, NEmpty, NPagination, useMessage } from "naive-ui"
import { computed, onBeforeMount, ref, useTemplateRef, watch } from "vue"
import { useI18n } from "vue-i18n"
import Api from "@/api"
import Chip from "@/components/common/Chip.vue"
import CustomerName from "@/components/common/CustomerName.vue"
import Icon from "@/components/common/Icon.vue"
import { useLatestRequest } from "@/composables/common/useLatestRequest"
import { useNavigation } from "@/composables/common/useNavigation"
import { useCustomerFilterStore } from "@/stores/customerFilter"
import { useSettingsStore } from "@/stores/settings"
import { CUSTOM_LIBRARY_CARD } from "@/types/siem"
import { getApiErrorMessage } from "@/utils"
import { formatDate } from "@/utils/format"

const emit = defineEmits<{
	(e: "loaded", value: EnabledDashboard[]): void
	(e: "loading", value: boolean): void
}>()

const customerFilterStore = useCustomerFilterStore()
const { routeDashboardViewer } = useNavigation()
const message = useMessage()
const { t } = useI18n()
const { loading, run } = useLatestRequest()
const dFormats = useSettingsStore().dateFormat

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
		title: t("dashboards.list.columns.dashboard"),
		key: "display_name",
		fixed: simpleMode.value ? undefined : "left",
		width: 280,
		render: row => <div>{row.display_name}</div>
	},
	{
		title: t("common.fields.customer"),
		key: "customer_code",
		width: 150,
		render: row => <CustomerName code={row.customer_code} />
	},
	{
		title: t("dashboards.list.columns.category"),
		key: "library_card",
		width: 230,
		render: row => <div>{row.library_card === CUSTOM_LIBRARY_CARD ? t("dashboards.list.custom") : row.library_card}</div>
	},
	{
		title: t("dashboards.list.columns.template"),
		key: "template_id",
		render: row => <div>{row.template_id}</div>
	},
	{
		title: t("common.fields.created"),
		key: "created_at",
		width: 180,
		render: row => <div>{formatDate(row.created_at, dFormats.datetime)}</div>
	},
	{
		title: t("common.fields.actions"),
		key: "actions",
		width: 180,
		render: row => {
			return (
				<NButton
					onClick={() => routeDashboardViewer(row.id).navigate()}
					v-slots={{
						icon: () => <Icon name="carbon:launch" />
					}}
				>
					{t("dashboards.list.view")}
				</NButton>
			)
		}
	}
])

function loadDashboards() {
	return run(
		async signal => {
			const response = await Api.siem.getEnabledDashboardsForCustomers(
				customerFilterStore.queryCustomerCodes,
				signal
			)

			data.value = response.data?.enabled_dashboards || []
			emit("loaded", data.value)
		},
		err => message.error(getApiErrorMessage(err as ApiError))
	)
}

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

// Re-fetch when the global customer filter changes (the list is scoped server-side).
watch(
	() => customerFilterStore.queryCustomerCodes,
	() => {
		pagination.value.page = 1
		loadDashboards()
	}
)

onBeforeMount(() => {
	loadDashboards()
})
</script>
