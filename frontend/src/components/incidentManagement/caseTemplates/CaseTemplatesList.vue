<template>
	<div class="case-templates-list flex flex-col gap-4">
		<!-- Header / actions -->
		<div class="flex flex-wrap items-center justify-between gap-3">
			<div class="flex flex-col gap-1">
				<h2 class="text-lg font-semibold">Case Templates</h2>
				<p class="text-secondary text-sm">
					Reusable investigation playbooks. Templates are matched to new cases by
					customer + alert source on case creation, with priority
					customer+source &gt; customer-only &gt; source-only &gt; global default.
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
				<n-button size="small" type="primary" @click="openCreate">
					<template #icon><Icon name="carbon:add" :size="14" /></template>
					New template
				</n-button>
			</div>
		</div>

		<!-- Filters -->
		<div class="flex flex-wrap items-center gap-3">
			<n-input
				v-model:value="customerFilter"
				size="small"
				placeholder="Customer code (blank = all)"
				clearable
				style="width: 220px"
			/>
			<n-input
				v-model:value="sourceFilter"
				size="small"
				placeholder="Alert source (blank = all)"
				clearable
				style="width: 220px"
			/>
			<n-checkbox v-model:checked="includeGlobal" size="small">
				Include global / source-agnostic
			</n-checkbox>
			<n-button size="small" quaternary @click="fetchTemplates">
				<template #icon><Icon name="carbon:renew" :size="14" /></template>
				Refresh
			</n-button>
		</div>

		<n-divider class="!my-1" />

		<n-spin :show="loading">
			<n-data-table
				:columns="columns"
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
import type { CaseTemplate } from "@/types/incidentManagement/caseTemplates.d"
import {
	NButton,
	NCheckbox,
	NDataTable,
	NDivider,
	NInput,
	NModal,
	NSpin,
	NTag,
	useDialog,
	useMessage
} from "naive-ui"
import { computed, h, onMounted, ref, watch } from "vue"
import Icon from "@/components/common/Icon.vue"
import Api from "@/api"
import { formatDate } from "@/utils/format"
import CaseTemplateEditor from "./CaseTemplateEditor.vue"

const message = useMessage()
const dialog = useDialog()

const templates = ref<CaseTemplate[]>([])
const loading = ref(false)
const search = ref("")
const customerFilter = ref("")
const sourceFilter = ref("")
const includeGlobal = ref(true)

const showEditor = ref(false)
const editing = ref<CaseTemplate | null>(null)

const filteredRows = computed(() => {
	if (!search.value.trim()) return templates.value
	const needle = search.value.trim().toLowerCase()
	return templates.value.filter(
		t =>
			t.name.toLowerCase().includes(needle) ||
			(t.description ?? "").toLowerCase().includes(needle) ||
			(t.customer_code ?? "").toLowerCase().includes(needle) ||
			(t.source ?? "").toLowerCase().includes(needle)
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
						? h(
								NTag,
								{ size: "tiny", type: "info", bordered: false } as any,
								{ default: () => "default" }
							)
						: null
				]),
				row.description
					? h("span", { class: "text-secondary text-xs" }, row.description)
					: null
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
				mandatory > 0
					? h("span", { class: "text-warning" }, `${mandatory} mandatory`)
					: null
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
						onClick: () => confirmDelete(row)
					} as any,
					{ default: () => "Delete" }
				)
			])
		}
	}
]

function fetchTemplates() {
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
			message.error(err.response?.data?.message || "Failed to load templates")
		})
		.finally(() => {
			loading.value = false
		})
}

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
					message.error(err.response?.data?.message || "Failed to delete template")
				})
		}
	})
}

// Re-fetch when scope filters change so the result set follows the
// backend's customer+source filtering semantics.
watch([customerFilter, sourceFilter, includeGlobal], () => {
	fetchTemplates()
})

onMounted(fetchTemplates)
</script>
