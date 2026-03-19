<template>
	<n-card v-if="visible" size="small">
		<template #header>
			<div class="flex items-center justify-between">
				<span>Enabled Dashboards</span>
				<span class="text-sm font-normal opacity-60">{{ enabledDashboards.length }} enabled</span>
			</div>
		</template>

		<n-scrollbar x-scrollable class="max-w-full">
			<n-spin :show="loadingEnabled">
				<n-data-table
					v-if="enabledDashboards.length"
					:columns="enabledColumns"
					:data="enabledDashboards"
					:bordered="false"
					:single-line="false"
					size="small"
				/>
				<n-empty
					v-else-if="!loadingEnabled"
					description="No dashboards enabled for this customer yet"
					class="h-32 justify-center"
				/>
			</n-spin>
		</n-scrollbar>
	</n-card>
</template>

<script setup lang="ts">
import type { DataTableColumns } from "naive-ui"
import type { EnabledDashboard } from "@/types/dashboards.d"
import type { EventSource } from "@/types/eventSources.d"
import { NButton, NCard, NDataTable, NEmpty, NScrollbar, NSpin, useDialog, useMessage } from "naive-ui"
import { computed, h, ref, watch } from "vue"
import { useRouter } from "vue-router"
import Api from "@/api"

const props = defineProps<{
	customerCode: string | null
	visible: boolean
	eventSourcesList: EventSource[]
}>()

const enabledDashboards = defineModel<EnabledDashboard[]>("enabledDashboards", { default: () => [] })

const loadingEnabled = ref(false)

const message = useMessage()
const dialog = useDialog()
const router = useRouter()

function fetchEnabledDashboards(customerCode: string) {
	loadingEnabled.value = true

	Api.siem
		.getEnabledDashboards(customerCode)
		.then(res => {
			if (res.data.success) {
				enabledDashboards.value = res.data?.enabled_dashboards || []
			} else {
				message.warning(res.data?.message || "An error occurred. Please try again later.")
			}
		})
		.catch(err => {
			message.error(err.response?.data?.message || "An error occurred. Please try again later.")
		})
		.finally(() => {
			loadingEnabled.value = false
		})
}

function refreshEnabledDashboards() {
	const code = props.customerCode
	if (code) {
		fetchEnabledDashboards(code)
	}
}

watch(
	() => props.customerCode,
	code => {
		if (!code) {
			loadingEnabled.value = false
			enabledDashboards.value = []
			return
		}
		fetchEnabledDashboards(code)
	},
	{ immediate: true }
)

defineExpose({
	refreshEnabledDashboards
})

const enabledColumns = computed<DataTableColumns<EnabledDashboard>>(() => [
	{ title: "Display Name", key: "display_name", minWidth: 180 },
	{ title: "Category", key: "library_card", width: 150 },
	{ title: "Template", key: "template_id", width: 180 },
	{
		title: "Event Source",
		key: "event_source_id",
		width: 180,
		render(row) {
			const source = props.eventSourcesList.find(s => s.id === row.event_source_id)
			return source ? `${source.name} (${source.event_type})` : `#${row.event_source_id}`
		}
	},
	{
		title: "Created",
		key: "created_at",
		width: 180,
		render(row) {
			return new Date(row.created_at).toLocaleString()
		}
	},
	{
		title: "",
		key: "actions",
		width: 160,
		render(row) {
			return h("div", { class: "flex gap-2" }, [
				h(
					NButton,
					{
						size: "small",
						type: "primary",
						quaternary: true,
						onClick: () => {
							// TODO-FE: use route by name instead of hardcoding the path
							router.push(`/dashboards/view/${row.id}`)
						}
					},
					{ default: () => "View" }
				),
				h(
					NButton,
					{
						size: "small",
						type: "error",
						quaternary: true,
						onClick: () => {
							dialog.warning({
								title: "Disable Dashboard",
								content: `Are you sure you want to disable "${row.display_name}"?`,
								positiveText: "Disable",
								negativeText: "Cancel",
								onPositiveClick: () => {
									Api.siem
										.disableDashboard(row.id)
										.then(res => {
											if (res.data.success) {
												message.success("Dashboard disabled successfully")
												refreshEnabledDashboards()
											} else {
												message.warning(
													res.data?.message || "An error occurred. Please try again later."
												)
											}
										})
										.catch(err => {
											message.error(
												err.response?.data?.message ||
													"An error occurred. Please try again later."
											)
										})
								}
							})
						}
					},
					{ default: () => "Disable" }
				)
			])
		}
	}
])
</script>
