<template>
	<n-form ref="formRef" :model="form" :rules="formRules" label-placement="top">
		<n-form-item label="Name" path="name">
			<n-input v-model:value="form.name" placeholder="e.g., Wazuh — Default" />
		</n-form-item>

		<n-form-item label="Description" path="description">
			<n-input
				v-model:value="form.description"
				type="textarea"
				placeholder="What this template is for"
				:autosize="{ minRows: 2, maxRows: 4 }"
			/>
		</n-form-item>

		<div class="grid grid-cols-2 gap-4">
			<n-form-item label="Customer code" path="customer_code">
				<n-input
					v-model:value="form.customer_code"
					placeholder="Leave empty for global"
					clearable
				/>
			</n-form-item>
			<n-form-item label="Alert source" path="source">
				<n-input
					v-model:value="form.source"
					placeholder="e.g., wazuh (leave empty for any)"
					clearable
				/>
			</n-form-item>
		</div>

		<n-form-item path="is_default">
			<n-checkbox v-model:checked="form.is_default">
				Default for this (customer, source) scope
			</n-checkbox>
		</n-form-item>

		<n-divider title-placement="left">Tasks</n-divider>

		<div v-if="props.template == null" class="text-secondary mb-2 text-xs">
			Add at least one task. You can edit / reorder tasks after the template is created.
		</div>
		<div v-else class="text-secondary mb-2 text-xs">
			Tasks below are saved immediately on add / edit / delete. Editing the template
			does NOT mutate task snapshots already attached to real cases.
		</div>

		<div class="flex flex-col gap-2">
			<div
				v-for="(task, idx) in tasks"
				:key="task._key"
				class="border-border rounded-md border p-3"
			>
				<div class="mb-2 flex items-center gap-2">
					<n-input
						v-model:value="task.title"
						size="small"
						placeholder="Task title"
						style="flex: 1"
						@blur="saveTask(idx)"
					/>
					<n-checkbox v-model:checked="task.mandatory" @update:checked="saveTask(idx)">
						mandatory
					</n-checkbox>
					<n-button-group size="tiny">
						<n-button :disabled="idx === 0" @click="moveTask(idx, -1)">
							<template #icon><Icon name="carbon:arrow-up" :size="14" /></template>
						</n-button>
						<n-button :disabled="idx === tasks.length - 1" @click="moveTask(idx, 1)">
							<template #icon><Icon name="carbon:arrow-down" :size="14" /></template>
						</n-button>
					</n-button-group>
					<n-button size="tiny" type="error" quaternary @click="deleteTask(idx)">
						<template #icon><Icon name="carbon:trash-can" :size="14" /></template>
					</n-button>
				</div>
				<n-input
					v-model:value="task.description"
					size="small"
					placeholder="Description (optional)"
					:autosize="{ minRows: 1, maxRows: 3 }"
					type="textarea"
					class="mb-2"
					@blur="saveTask(idx)"
				/>
				<n-input
					v-model:value="task.guidelines"
					size="small"
					placeholder="Guidelines / best practices (optional)"
					:autosize="{ minRows: 1, maxRows: 5 }"
					type="textarea"
					@blur="saveTask(idx)"
				/>
			</div>

			<n-button size="small" dashed @click="addTask">
				<template #icon><Icon name="carbon:add" :size="14" /></template>
				Add task
			</n-button>
		</div>

		<div class="mt-4 flex justify-end gap-2">
			<n-button @click="emit('cancel')">Cancel</n-button>
			<n-button type="primary" :loading="saving" @click="handleSave">
				{{ props.template ? "Save changes" : "Create template" }}
			</n-button>
		</div>
	</n-form>
</template>

<script setup lang="ts">
import type { FormInst, FormRules } from "naive-ui"
import type { CaseTemplate } from "@/types/incidentManagement/caseTemplates.d"
import {
	NButton,
	NButtonGroup,
	NCheckbox,
	NDivider,
	NForm,
	NFormItem,
	NInput,
	useMessage
} from "naive-ui"
import { ref, watch } from "vue"
import Icon from "@/components/common/Icon.vue"
import Api from "@/api"

interface DraftTask {
	_key: string // stable client-side key for v-for
	id?: number // present when persisted (template_task_id from backend)
	title: string
	description: string
	guidelines: string
	mandatory: boolean
	order_index: number
}

const props = defineProps<{
	template: CaseTemplate | null
}>()
const emit = defineEmits<{
	(e: "saved", template: CaseTemplate): void
	(e: "cancel"): void
}>()

const message = useMessage()
const formRef = ref<FormInst | null>(null)
const saving = ref(false)

const form = ref({
	name: "",
	description: "",
	customer_code: "",
	source: "",
	is_default: false
})
const formRules: FormRules = {
	name: { required: true, message: "Name is required", trigger: "blur" }
}

const tasks = ref<DraftTask[]>([])

let keyCounter = 0
function nextKey() {
	keyCounter += 1
	return `t${Date.now()}-${keyCounter}`
}

function loadFromTemplate(t: CaseTemplate | null) {
	if (t) {
		form.value = {
			name: t.name,
			description: t.description ?? "",
			customer_code: t.customer_code ?? "",
			source: t.source ?? "",
			is_default: t.is_default
		}
		tasks.value = (t.tasks ?? []).map(task => ({
			_key: nextKey(),
			id: task.id,
			title: task.title,
			description: task.description ?? "",
			guidelines: task.guidelines ?? "",
			mandatory: task.mandatory,
			order_index: task.order_index
		}))
	} else {
		form.value = { name: "", description: "", customer_code: "", source: "", is_default: false }
		tasks.value = [
			{
				_key: nextKey(),
				title: "",
				description: "",
				guidelines: "",
				mandatory: false,
				order_index: 0
			}
		]
	}
}

watch(() => props.template, loadFromTemplate, { immediate: true })

function addTask() {
	tasks.value.push({
		_key: nextKey(),
		title: "",
		description: "",
		guidelines: "",
		mandatory: false,
		order_index: tasks.value.length
	})
}

async function deleteTask(idx: number) {
	const task = tasks.value[idx]
	// If the template hasn't been created yet, just drop the row.
	if (!props.template || task.id == null) {
		tasks.value.splice(idx, 1)
		return
	}
	try {
		const res = await Api.incidentManagement.caseTemplates.deleteTemplateTask(task.id)
		if (res.data.success) {
			tasks.value.splice(idx, 1)
		} else {
			message.warning(res.data.message)
		}
	} catch (err: any) {
		message.error(err.response?.data?.message || "Failed to delete task")
	}
}

async function moveTask(idx: number, delta: number) {
	const newIdx = idx + delta
	if (newIdx < 0 || newIdx >= tasks.value.length) return
	const moved = tasks.value.splice(idx, 1)[0]
	tasks.value.splice(newIdx, 0, moved)
	tasks.value.forEach((t, i) => (t.order_index = i))

	// If the template is persisted, push the reorder up to the backend.
	if (props.template) {
		const orderedIds = tasks.value.filter(t => t.id != null).map(t => t.id as number)
		if (orderedIds.length === tasks.value.length) {
			await Api.incidentManagement.caseTemplates
				.reorderTemplateTasks(props.template.id, orderedIds)
				.catch(err => {
					message.error(err.response?.data?.message || "Failed to reorder tasks")
				})
		}
	}
}

async function saveTask(idx: number) {
	if (!props.template) return // creation flow batches at submit time
	const draft = tasks.value[idx]
	if (!draft.title.trim()) return // skip empty drafts; user is still typing

	const payload = {
		title: draft.title,
		description: draft.description || null,
		guidelines: draft.guidelines || null,
		mandatory: draft.mandatory,
		order_index: draft.order_index
	}

	try {
		if (draft.id == null) {
			const res = await Api.incidentManagement.caseTemplates.addTemplateTask(
				props.template.id,
				payload
			)
			if (res.data.success && res.data.task) {
				draft.id = res.data.task.id
			} else {
				message.warning(res.data.message)
			}
		} else {
			const res = await Api.incidentManagement.caseTemplates.updateTemplateTask(draft.id, payload)
			if (!res.data.success) message.warning(res.data.message)
		}
	} catch (err: any) {
		message.error(err.response?.data?.message || "Failed to save task")
	}
}

async function handleSave() {
	try {
		await formRef.value?.validate()
	} catch {
		return
	}

	saving.value = true
	const payload = {
		name: form.value.name,
		description: form.value.description || null,
		customer_code: form.value.customer_code || null,
		source: form.value.source || null,
		is_default: form.value.is_default
	}

	try {
		if (props.template) {
			// Update flow — metadata only; task edits already streamed via saveTask.
			const res = await Api.incidentManagement.caseTemplates.updateTemplate(
				props.template.id,
				payload
			)
			if (res.data.success && res.data.template) {
				emit("saved", res.data.template)
			} else {
				message.warning(res.data.message)
			}
		} else {
			const cleanTasks = tasks.value
				.filter(t => t.title.trim().length > 0)
				.map(t => ({
					title: t.title,
					description: t.description || null,
					guidelines: t.guidelines || null,
					mandatory: t.mandatory,
					order_index: t.order_index
				}))
			const res = await Api.incidentManagement.caseTemplates.createTemplate({
				...payload,
				tasks: cleanTasks
			})
			if (res.data.success && res.data.template) {
				emit("saved", res.data.template)
			} else {
				message.warning(res.data.message)
			}
		}
	} catch (err: any) {
		message.error(err.response?.data?.message || "Failed to save template")
	} finally {
		saving.value = false
	}
}
</script>
