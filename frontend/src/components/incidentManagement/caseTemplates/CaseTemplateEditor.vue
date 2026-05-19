<template>
	<n-form ref="formRef" :model="form" :rules="formRules" label-placement="top" :disabled="saving">
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
			<n-form-item label="Customer code" path="customer_code" :show-feedback="false">
				<n-select
					v-model:value="form.customer_code"
					:options="customersOptions"
					placeholder="Leave empty for global"
					:loading="loadingCustomers"
					filterable
					clearable
					:consistent-menu-width="false"
				/>
			</n-form-item>
			<n-form-item label="Alert source" path="source" :show-feedback="false">
				<n-select
					v-model:value="form.source"
					:options="sourcesOptions"
					:consistent-menu-width="false"
					placeholder="e.g., wazuh (leave empty for any)"
					filterable
					clearable
					:loading="loadingConfiguredSources"
				/>
			</n-form-item>
		</div>

		<n-form-item path="is_default">
			<n-checkbox v-model:checked="form.is_default">Default for this (customer, source) scope</n-checkbox>
		</n-form-item>

		<!--
		Conditional auto-apply. Both inputs must be filled (or both empty) — the
		backend rejects half-set pairs because a partial condition would silently
		never trigger. Example: field "data_win_system_eventID", value "1" applies
		this template only to Sysmon Event ID 1 events.
		-->
		<n-card size="small" title="Conditional auto-apply (optional)">
			<template #header-extra>
				<div v-if="matchHalfSet" class="text-warning text-xs">
					Both field and value are required
				</div>
			</template>
			<p class="text-secondary mb-2 text-xs">
				When set, auto-apply only fires if the originating Wazuh document has
				<code>{{ form.match_field || "<field>" }}</code>
				equal to
				<code>{{ form.match_value || "<value>" }}</code>
				. Leave blank for an unconditional template.
			</p>
			<div class="grid grid-cols-1 gap-3 @md:grid-cols-2">
				<n-form-item label="Match field" path="match_field" :show-feedback="false">
					<n-input
						v-model:value="form.match_field"
						placeholder="e.g., data_win_system_eventID"
					/>
				</n-form-item>
				<n-form-item label="Match value" path="match_value" :show-feedback="false">
					<n-input v-model:value="form.match_value" placeholder="e.g., 1" />
				</n-form-item>
			</div>
		</n-card>

		<n-card size="small" title="Tasks" content-class="flex flex-col gap-3">
			<template #header-extra>
				<div
					v-if="taskSaving"
					class="text-secondary text-xs opacity-0 transition-opacity duration-300"
					:class="{ 'animate-pulse opacity-100': taskSaving }"
				>
					saving...
				</div>
			</template>
			<p v-if="props.template == null" class="text-xs">
				Add at least one task. You can edit / reorder tasks after the template is created.
			</p>
			<p v-else class="text-xs">
				Tasks below are saved immediately on add / edit / delete. Editing the template does NOT mutate task
				snapshots already attached to real cases.
			</p>

			<div class="flex flex-col gap-2">
				<CardEntity v-for="(task, idx) in tasks" :key="task._key" embedded size="small">
					<div class="flex flex-col gap-2">
						<div class="flex items-center gap-2">
							<n-input
								v-model:value="task.title"
								size="small"
								placeholder="Task title"
								class="flex-1"
								@blur="saveTask(idx)"
							/>
							<n-checkbox v-model:checked="task.mandatory" @update:checked="saveTask(idx)">
								mandatory
							</n-checkbox>
							<n-button-group v-if="tasks.length > 1" size="tiny">
								<n-button :disabled="idx === 0" @click="moveTask(idx, -1)">
									<template #icon><Icon name="carbon:arrow-up" /></template>
								</n-button>
								<n-button :disabled="idx === tasks.length - 1" @click="moveTask(idx, 1)">
									<template #icon><Icon name="carbon:arrow-down" /></template>
								</n-button>
							</n-button-group>
							<n-button
								v-if="tasks.length > 1"
								size="tiny"
								type="error"
								quaternary
								@click="deleteTask(idx)"
							>
								<template #icon><Icon name="carbon:trash-can" /></template>
							</n-button>
						</div>
						<n-input
							v-model:value="task.description"
							size="small"
							placeholder="Description (optional)"
							:autosize="{ minRows: 1, maxRows: 3 }"
							type="textarea"
							clearable
							@blur="saveTask(idx)"
						/>
						<n-input
							v-model:value="task.guidelines"
							size="small"
							placeholder="Guidelines / best practices (optional)"
							:autosize="{ minRows: 1, maxRows: 5 }"
							type="textarea"
							clearable
							@blur="saveTask(idx)"
						/>
					</div>
				</CardEntity>

				<n-button size="small" dashed @click="addTask">
					<template #icon><Icon name="carbon:add" /></template>
					Add task
				</n-button>
			</div>
		</n-card>

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
import type { ApiError } from "@/types/common"
import type { Customer } from "@/types/customers"
import type { CaseTemplate } from "@/types/incidentManagement/caseTemplates.d"
import type { SourceName } from "@/types/incidentManagement/sources"
import { NButton, NButtonGroup, NCard, NCheckbox, NForm, NFormItem, NInput, NSelect, useMessage } from "naive-ui"
import { computed, onBeforeMount, ref, watch } from "vue"
import Api from "@/api"
import CardEntity from "@/components/common/cards/CardEntity.vue"
import Icon from "@/components/common/Icon.vue"
import { getApiErrorMessage } from "@/utils"

interface DraftTask {
	_key: string // stable client-side key for v-for
	id?: number // present when persisted (template_task_id from backend)
	title: string
	description: string
	guidelines: string
	mandatory: boolean
	order_index: number
}

interface FormModel {
	name: string | null
	description: string | null
	customer_code: string | null
	source: string | null
	is_default: boolean
	match_field: string | null
	match_value: string | null
}

const props = defineProps<{
	template?: CaseTemplate | null
}>()

const emit = defineEmits<{
	(e: "saved", template: CaseTemplate): void
	(e: "cancel"): void
}>()

const message = useMessage()
const formRef = ref<FormInst | null>(null)
const saving = ref(false)
const taskSaving = ref(false)

const loadingCustomers = ref(false)
const customersList = ref<Customer[]>([])
const customersOptions = computed(() =>
	customersList.value.map(o => ({ label: `#${o.customer_code} - ${o.customer_name}`, value: o.customer_code }))
)

const loadingConfiguredSources = ref(false)
const configuredSourcesList = ref<SourceName[]>([])
const sourcesOptions = computed(() => configuredSourcesList.value.map(o => ({ label: o, value: o })))

const form = ref<FormModel>({
	name: null,
	description: null,
	customer_code: null,
	source: null,
	is_default: false,
	match_field: null,
	match_value: null
})

const matchHalfSet = computed(() => {
	const hasField = !!form.value.match_field?.trim()
	const hasValue = !!form.value.match_value?.trim()
	return hasField !== hasValue
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

function loadFromTemplate(t?: CaseTemplate | null) {
	if (t) {
		form.value = {
			name: t.name,
			description: t.description ?? "",
			customer_code: t.customer_code ?? "",
			source: t.source ?? "",
			is_default: t.is_default,
			match_field: t.match_field ?? null,
			match_value: t.match_value ?? null
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
		form.value = {
			name: null,
			description: null,
			customer_code: null,
			source: null,
			is_default: false,
			match_field: null,
			match_value: null
		}
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

	taskSaving.value = true
	try {
		const res = await Api.incidentManagement.caseTemplates.deleteTemplateTask(task.id)
		if (res.data.success) {
			tasks.value.splice(idx, 1)
		} else {
			message.warning(res.data.message)
		}
	} catch (err) {
		message.error(getApiErrorMessage(err as ApiError) || "Failed to delete task")
	} finally {
		taskSaving.value = false
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
			taskSaving.value = true
			try {
				await Api.incidentManagement.caseTemplates.reorderTemplateTasks(props.template.id, orderedIds)
			} catch (err) {
				message.error(getApiErrorMessage(err as ApiError) || "Failed to reorder tasks")
			} finally {
				taskSaving.value = false
			}
		}
	}
}

async function saveTask(idx: number) {
	if (!props.template) return // creation flow batches at submit time

	const draft = tasks.value[idx]

	if (!draft.title.trim()) return // skip empty drafts; user is still typing

	taskSaving.value = true

	const payload = {
		title: draft.title,
		description: draft.description || null,
		guidelines: draft.guidelines || null,
		mandatory: draft.mandatory,
		order_index: draft.order_index
	}

	try {
		if (draft.id == null) {
			const res = await Api.incidentManagement.caseTemplates.addTemplateTask(props.template.id, payload)
			if (res.data.success && res.data.task) {
				draft.id = res.data.task.id
			} else {
				message.warning(res.data.message)
			}
		} else {
			const res = await Api.incidentManagement.caseTemplates.updateTemplateTask(draft.id, payload)
			if (!res.data.success) message.warning(res.data.message)
		}
	} catch (err) {
		message.error(getApiErrorMessage(err as ApiError) || "Failed to save task")
	} finally {
		taskSaving.value = false
	}
}

async function handleSave() {
	try {
		await formRef.value?.validate()
	} catch {
		return
	}

	if (matchHalfSet.value) {
		message.warning("Match field and match value must both be set or both be empty.")
		return
	}

	saving.value = true

	const payload = {
		name: form.value.name || "",
		description: form.value.description || null,
		customer_code: form.value.customer_code || null,
		source: form.value.source || null,
		is_default: form.value.is_default,
		match_field: form.value.match_field?.trim() || null,
		match_value: form.value.match_value?.trim() || null
	}

	try {
		if (props.template) {
			// Update flow — metadata only; task edits already streamed via saveTask.
			const res = await Api.incidentManagement.caseTemplates.updateTemplate(props.template.id, payload)
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
	} catch (err) {
		message.error(getApiErrorMessage(err as ApiError) || "Failed to save template")
	} finally {
		saving.value = false
	}
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
			message.error(getApiErrorMessage(err as ApiError) || "An error occurred. Please try again later.")
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
			message.error(getApiErrorMessage(err as ApiError) || "An error occurred. Please try again later.")
		})
		.finally(() => {
			loadingConfiguredSources.value = false
		})
}

watch(() => props.template, loadFromTemplate, { immediate: true })

onBeforeMount(() => {
	getCustomers()
	getConfiguredSources()
})
</script>
