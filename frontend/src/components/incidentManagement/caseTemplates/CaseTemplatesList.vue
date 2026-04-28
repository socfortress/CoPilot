<template>
	<div class="case-templates-list flex flex-col gap-4">
		<!-- Header / actions -->

		<div class="flex flex-col gap-2">
			<div class="flex items-center gap-4">
				<h2>Case Templates</h2>
				<n-button size="small" secondary type="primary" @click="openCreate">
					<template #icon><Icon name="carbon:add" /></template>
					New template
				</n-button>
			</div>
			<p>
				Reusable investigation playbooks. Templates are matched to new cases by customer + alert source on case
				creation, with priority customer+source &gt; customer-only &gt; source-only &gt; global default.
			</p>
		</div>

		<!-- Filters -->
		<div class="@container mt-4 grid grid-cols-12 items-center gap-3">
			<n-input
				v-model:value="search"
				size="small"
				placeholder="Search by name or description"
				clearable
				class="col-span-full @3xl:col-span-4 @6xl:col-span-5"
			>
				<template #prefix><Icon name="carbon:search" /></template>
			</n-input>
			<n-select
				v-model:value="customerFilter"
				size="small"
				:options="customersOptions"
				placeholder="Customer code (blank = all)"
				:loading="loadingCustomers"
				filterable
				clearable
				class="col-span-full @lg:col-span-6 @3xl:col-span-3"
				:consistent-menu-width="false"
			/>
			<n-select
				v-model:value="sourceFilter"
				:options="sourcesOptions"
				:consistent-menu-width="false"
				placeholder="Alert source (blank = all)"
				size="small"
				filterable
				clearable
				class="col-span-full @lg:col-span-6 @3xl:col-span-3 @6xl:col-span-2"
				:loading="loadingConfiguredSources"
			/>
			<n-checkbox v-model:checked="includeGlobal" size="small" class="col-span-full @3xl:col-span-2">
				<div class="text-xs">Include global / source-agnostic</div>
			</n-checkbox>
		</div>

		<n-spin :show="loading">
			<n-data-table :columns :data="filteredRows" size="small" />
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
import { computed, onBeforeMount, ref, watch } from "vue"
import Api from "@/api"
import Icon from "@/components/common/Icon.vue"
import { useSettingsStore } from "@/stores/settings"
import { getApiErrorMessage } from "@/utils"
import { formatDate } from "@/utils/format"
import CaseTemplateEditor from "./CaseTemplateEditor.vue"

const message = useMessage()
const dialog = useDialog()

const dFormats = useSettingsStore().dateFormat
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

function renderCustomerCode(customerCode: string | null | undefined) {
	if (customerCode) {
		return <span class="font-mono">{customerCode}</span>
	}

	return <em class="text-tertiary">any</em>
}

function renderSource(source: string | null | undefined) {
	if (source) {
		return <span class="font-mono">{source}</span>
	}

	return <em class="text-tertiary">any</em>
}

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
		className: "whitespace-nowrap",
		render: row => (
			<div class="flex flex-col gap-1">
				<div class="flex items-center gap-2">
					<span class="font-medium whitespace-nowrap">{row.name}</span>
					{row.is_default && (
						<NTag size="tiny" type="info" bordered={false}>
							default
						</NTag>
					)}
				</div>
				{row.description && <span class="text-secondary text-xs">{row.description}</span>}
			</div>
		)
	},
	{
		title: "Scope",
		key: "scope",
		className: "whitespace-nowrap",
		render: row => (
			<div class="flex flex-col text-sm whitespace-nowrap">
				<span>
					<span class="text-secondary">customer: </span>
					{renderCustomerCode(row.customer_code)}
				</span>
				<span>
					<span class="text-secondary">source: </span>
					{renderSource(row.source)}
				</span>
			</div>
		)
	},
	{
		title: "Tasks",
		key: "tasks",
		width: 110,
		className: "whitespace-nowrap",
		render(row) {
			const total = row.tasks?.length ?? 0
			const mandatory = row.tasks?.filter(t => t.mandatory).length ?? 0

			return (
				<div class="flex flex-col text-sm whitespace-nowrap">
					<span>
						<span class="font-mono">{total}</span>
						{" total"}
					</span>
					{mandatory > 0 && (
						<span class="text-warning">
							<span class="font-mono">{mandatory}</span>
							{" mandatory"}
						</span>
					)}
				</div>
			)
		}
	},
	{
		title: "Created by",
		key: "created_by",
		className: "whitespace-nowrap",
		render: row => <span class="whitespace-nowrap">{row.created_by}</span>
	},
	{
		title: "Updated",
		key: "updated_at",
		className: "whitespace-nowrap",
		render: row => (
			<span class="font-mono text-xs whitespace-nowrap">{formatDate(row.updated_at, dFormats.datetime)}</span>
		)
	},
	{
		title: "Actions",
		key: "actions",
		width: 120,
		className: "whitespace-nowrap",
		render: row => (
			<div class="flex gap-2">
				<NButton
					size="small"
					secondary
					onClick={() => openEdit(row)}
					v-slots={{ icon: () => <Icon name="carbon:edit" size={14} /> }}
				>
					Edit
				</NButton>
				<NButton
					size="small"
					secondary
					type="error"
					loading={deletingId.value === row.id}
					onClick={() => confirmDelete(row)}
					v-slots={{ icon: () => <Icon name="carbon:trash-can" size={14} /> }}
				>
					Delete
				</NButton>
			</div>
		)
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
		title: `Delete template "${row.name}" ?`,
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
