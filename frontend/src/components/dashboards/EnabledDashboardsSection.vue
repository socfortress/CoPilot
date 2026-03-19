<template>
	<n-card v-if="visible" ref="wrapperRef" size="small">
		<template #header>Enabled Dashboards</template>
		<template #header-extra>
			<span class="text-secondary text-sm">{{ enabledDashboards.length }} enabled</span>
		</template>

		<n-data-table
			bordered
			:loading="loadingEnabled"
			size="small"
			:data="enabledDashboards"
			:columns="enabledColumns"
			:scroll-x="600"
			:pagination="false"
			class="[&_.n-data-table-th\_\_title]:whitespace-nowrap"
		>
			<template #empty>
				<n-empty description="No enabled dashboards" />
			</template>
		</n-data-table>
	</n-card>
</template>

<script setup lang="ts">
import type { DataTableColumns } from "naive-ui"
import type { EnabledDashboard } from "@/types/dashboards.d"
import type { EventSource } from "@/types/eventSources.d"
import { useElementSize } from "@vueuse/core"
import { NButton, NCard, NDataTable, NEmpty, NScrollbar, NSpin, useDialog, useMessage } from "naive-ui"
import { computed, h, ref, useTemplateRef, watch } from "vue"
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
const { width: headerWidthRef } = useElementSize(useTemplateRef("wrapperRef"))
const router = useRouter()
const simpleMode = computed(() => headerWidthRef.value < 600)

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
	{ title: "Display Name", key: "display_name", minWidth: 240 },
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
		fixed: simpleMode.value ? undefined : "right",
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
