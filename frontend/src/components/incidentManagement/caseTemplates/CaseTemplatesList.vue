<template>
	<div class="case-templates-list flex flex-col gap-4">
		<!-- Header / actions -->
		<div class="flex flex-wrap items-center justify-between gap-3">
			<div class="flex flex-col gap-2">
				<div class="flex items-center gap-4">
					<h3>Case Templates</h3>
					<n-button size="small" secondary type="primary" @click="openCreate">
						<template #icon><Icon name="carbon:add" /></template>
						New template
					</n-button>
				</div>
				<p class="text-sm">
					Reusable investigation playbooks. Templates are matched to new cases by customer + alert source on
					case creation, with priority customer+source &gt; customer-only &gt; source-only &gt; global
					default.
				</p>
			</div>
			<div class="flex items-center gap-2">
				<n-input
					v-model:value="search"
					size="small"
					placeholder="Search by name or description"
					clearable
					style="width: 240px"
				>
					<template #prefix><Icon name="carbon:search" :size="14" /></template>
				</n-input>
			</div>
		</div>

		<!-- Filters -->
		<div class="flex flex-wrap items-center gap-3">
			<n-select
				v-model:value="customerFilter"
				size="small"
				:options="customersOptions"
				placeholder="Customer code (blank = all)"
				:loading="loadingCustomers"
				filterable
				class="w-50!"
				:consistent-menu-width="false"
			/>
			<n-select
				v-model:value="sourceFilter"
				:options="sourcesOptions"
				placeholder="Alert source (blank = all)"
				size="small"
				filterable
				clearable
				class="w-44!"
				:loading="loadingConfiguredSources"
			/>
			<n-checkbox v-model:checked="includeGlobal" size="small">Include global / source-agnostic</n-checkbox>
		</div>

		<n-spin :show="loading">
			<n-data-table
				:columns
				:data="filteredRows"
				:row-key="(row: CaseTemplate) => row.id"
				:bordered="false"
				size="small"
			/>
		</n-spin>

		<!-- Editor modal -->
		<n-modal
			v-model:show="showEditor"
			preset="card"
			:title="editing ? `Edit template — ${editing.name}` : 'New template'"
			style="max-width: 720px"
		>
			<CaseTemplateEditor
				v-if="showEditor"
				:template="editing"
				@saved="onTemplateSaved"
				@cancel="showEditor = false"
			/>
		</n-modal>
	</div>
</template>

<script setup lang="tsx">
import type { DataTableColumns } from "naive-ui"
import type { ApiError } from "@/types/common"
import type { Customer } from "@/types/customers"
import type { CaseTemplate } from "@/types/incidentManagement/caseTemplates.d"
import type { SourceName } from "@/types/incidentManagement/sources"
import { useDebounceFn } from "@vueuse/core"
import { NButton, NCheckbox, NDataTable, NInput, NModal, NSelect, NSpin, NTag, useDialog, useMessage } from "naive-ui"
import { computed, h, onBeforeMount, ref, watch } from "vue"
import Api from "@/api"
import Icon from "@/components/common/Icon.vue"
import { getApiErrorMessage } from "@/utils"
import { formatDate } from "@/utils/format"
import CaseTemplateEditor from "./CaseTemplateEditor.vue"

const message = useMessage()
const dialog = useDialog()

const templates = ref<CaseTemplate[]>([])
const loading = ref(false)
const deletingId = ref<number | null>(null)
const search = ref<string | null>(null)
const customerFilter = ref<string | null>(null)
const sourceFilter = ref<string | null>(null)
const includeGlobal = ref(true)

const loadingCustomers = ref(false)
const customersList = ref<Customer[]>([])
const customersOptions = computed(() =>
	customersList.value.map(o => ({ label: `#${o.customer_code} - ${o.customer_name}`, value: o.customer_code }))
)

const loadingConfiguredSources = ref(false)
const configuredSourcesList = ref<SourceName[]>([])
const sourcesOptions = computed(() => configuredSourcesList.value.map(o => ({ label: o, value: o })))

const showEditor = ref(false)
const editing = ref<CaseTemplate | null>(null)

const filteredRows = computed(() => {
	if (!search.value?.trim()) return templates.value

	const text = search.value.trim().toLowerCase()

	return templates.value.filter(
		t =>
			t.name.toLowerCase().includes(text) ||
			(t.description ?? "").toLowerCase().includes(text) ||
			(t.customer_code ?? "").toLowerCase().includes(text) ||
			(t.source ?? "").toLowerCase().includes(text)
	)
})

const columns: DataTableColumns<CaseTemplate> = [
	{
		title: "Name",
		key: "name",
		render(row) {
			return h("div", { class: "flex flex-col gap-1" }, [
				h("div", { class: "flex items-center gap-2" }, [
					h("span", { class: "font-medium" }, row.name),
					row.is_default
						? h(NTag, { size: "tiny", type: "info", bordered: false } as any, { default: () => "default" })
						: null
				]),
				row.description ? h("span", { class: "text-secondary text-xs" }, row.description) : null
			])
		}
	},
	{
		title: "Scope",
		key: "scope",
		render(row) {
			return h("div", { class: "flex flex-col gap-1 text-xs" }, [
				h("span", null, [
					h("span", { class: "text-tertiary" }, "customer: "),
					row.customer_code ?? h("em", { class: "text-tertiary" }, "any")
				]),
				h("span", null, [
					h("span", { class: "text-tertiary" }, "source: "),
					row.source ?? h("em", { class: "text-tertiary" }, "any")
				])
			])
		}
	},
	{
		title: "Tasks",
		key: "tasks",
		width: 90,
		render(row) {
			const total = row.tasks?.length ?? 0
			const mandatory = row.tasks?.filter(t => t.mandatory).length ?? 0
			return h("div", { class: "flex flex-col text-xs" }, [
				h("span", null, `${total} total`),
				mandatory > 0 ? h("span", { class: "text-warning" }, `${mandatory} mandatory`) : null
			])
		}
	},
	{
		title: "Created by",
		key: "created_by",
		render: row => row.created_by
	},
	{
		title: "Updated",
		key: "updated_at",
		render: row => formatDate(row.updated_at, "MMM D, YYYY HH:mm") as string
	},
	{
		title: "Actions",
		key: "actions",
		width: 120,
		render(row) {
			return h("div", { class: "flex gap-2" }, [
				h(
					NButton,
					{
						size: "tiny",
						quaternary: true,
						onClick: () => openEdit(row)
					} as any,
					{ default: () => "Edit" }
				),
				h(
					NButton,
					{
						size: "tiny",
						quaternary: true,
						type: "error",
						loading: deletingId.value === row.id,
						onClick: () => confirmDelete(row)
					} as any,
					{ default: () => "Delete" }
				)
			])
		}
	}
]

const fetchTemplates = useDebounceFn(() => {
	loading.value = true

	Api.incidentManagement.caseTemplates
		.listTemplates({
			customerCode: customerFilter.value || undefined,
			source: sourceFilter.value || undefined,
			includeGlobal: includeGlobal.value
		})
		.then(res => {
			if (res.data.success) {
				templates.value = res.data.templates
			} else {
				message.warning(res.data.message)
			}
		})
		.catch(err => {
			message.error(getApiErrorMessage(err as ApiError) || "Failed to load templates")
		})
		.finally(() => {
			loading.value = false
		})
}, 400)

function openCreate() {
	editing.value = null
	showEditor.value = true
}

function openEdit(row: CaseTemplate) {
	editing.value = row
	showEditor.value = true
}

function onTemplateSaved() {
	showEditor.value = false
	fetchTemplates()
}

function confirmDelete(row: CaseTemplate) {
	dialog.warning({
		title: `Delete template "${row.name}"?`,
		content:
			"Deleting the template removes its task definitions. Existing CaseTask snapshots on real cases are preserved (they're independent of the template).",
		positiveText: "Delete",
		negativeText: "Cancel",
		onPositiveClick: () => {
			deletingId.value = row.id

			Api.incidentManagement.caseTemplates
				.deleteTemplate(row.id)
				.then(res => {
					if (res.data.success) {
						message.success(`Deleted "${row.name}"`)
						fetchTemplates()
					} else {
						message.warning(res.data.message)
					}
				})
				.catch(err => {
					message.error(getApiErrorMessage(err as ApiError) || "Failed to delete template")
				})
				.finally(() => {
					deletingId.value = null
				})
		}
	})
}

function getCustomers() {
	loadingCustomers.value = true

	Api.customers
		.getCustomers()
		.then(res => {
			if (res.data.success) {
				customersList.value = res.data?.customers || []
			} else {
				message.warning(res.data?.message || "An error occurred. Please try again later.")
			}
		})
		.catch(err => {
			message.error(err.response?.data?.message || "An error occurred. Please try again later.")
		})
		.finally(() => {
			loadingCustomers.value = false
		})
}

function getConfiguredSources() {
	loadingConfiguredSources.value = true

	Api.incidentManagement.sources
		.getConfiguredSources()
		.then(res => {
			if (res.data.success) {
				configuredSourcesList.value = res.data?.sources || []
			} else {
				message.warning(res.data?.message || "An error occurred. Please try again later.")
			}
		})
		.catch(err => {
			message.error(err.response?.data?.message || "An error occurred. Please try again later.")
		})
		.finally(() => {
			loadingConfiguredSources.value = false
		})
}

// Re-fetch when scope filters change so the result set follows the
// backend's customer+source filtering semantics.
watch([customerFilter, sourceFilter, includeGlobal], () => {
	fetchTemplates()
})

onBeforeMount(() => {
	fetchTemplates()
	getCustomers()
	getConfiguredSources()
})
</script>
