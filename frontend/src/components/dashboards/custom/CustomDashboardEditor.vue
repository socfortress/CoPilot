<template>
	<div class="flex flex-col gap-6">
		<!-- ── Metadata ─────────────────────────────────────────── -->
		<div class="flex flex-col gap-1">
			<p class="text-secondary text-sm">Dashboard</p>

			<div class="flex flex-wrap gap-4">
				<n-form-item label="Title" required class="min-w-60 grow">
					<n-input v-model:value="form.title" placeholder="e.g. Acronis - Overview" clearable />
				</n-form-item>

				<n-form-item label="Event type" class="min-w-40">
					<n-select v-model:value="form.event_type" :options="eventTypeOptions" filterable tag />
				</n-form-item>
			</div>

			<n-form-item label="Description">
				<n-input
					v-model:value="form.description"
					type="textarea"
					:autosize="{ minRows: 2, maxRows: 4 }"
					placeholder="What this dashboard shows"
					clearable
				/>
			</n-form-item>

			<div class="flex flex-wrap gap-4">
				<n-form-item label="Vendor" class="min-w-40 grow">
					<n-input v-model:value="form.vendor" placeholder="e.g. Acronis" clearable />
				</n-form-item>

				<n-form-item label="Product" class="min-w-40 grow">
					<n-input v-model:value="form.product" placeholder="e.g. Cyber Protect" clearable />
				</n-form-item>

				<n-form-item label="Icon" class="min-w-40">
					<n-select v-model:value="form.icon" :options="iconOptions" />
				</n-form-item>

				<n-form-item label="Accent color" class="min-w-32">
					<n-color-picker v-model:value="form.color" :show-alpha="false" :modes="['hex']" />
				</n-form-item>
			</div>

			<n-form-item label="Tags">
				<n-dynamic-tags v-model:value="form.tags" />
			</n-form-item>

			<n-form-item label="Dashboard filter (Lucene)">
				<n-input
					v-model:value="form.default_query"
					placeholder="* — applied on top of every widget filter"
					clearable
				/>
			</n-form-item>

			<n-form-item v-if="customerCode" label="Availability">
				<div class="flex flex-col gap-1">
					<n-checkbox v-model:checked="shareGlobally">Available to all customers</n-checkbox>
					<span class="text-secondary text-sm">
						{{
							shareGlobally
								? "Shared dashboards can be enabled for any customer, each against its own event source."
								: `Only available for #${customerCode}.`
						}}
					</span>
				</div>
			</n-form-item>
		</div>

		<!-- ── Widgets ──────────────────────────────────────────── -->
		<div class="flex flex-col gap-2">
			<div class="flex flex-wrap items-center justify-between gap-2">
				<p class="text-secondary text-sm">Widgets</p>
				<div class="flex flex-wrap gap-2">
					<n-button size="small" :disabled="!form.panels.length" @click="exportDefinition()">
						<template #icon>
							<Icon :name="ExportIcon" />
						</template>
						Export JSON
					</n-button>
					<n-button size="small" @click="showImport = true">
						<template #icon>
							<Icon :name="ImportIcon" />
						</template>
						Load JSON
					</n-button>
					<n-button size="small" type="primary" @click="openPanelForm(null)">
						<template #icon>
							<Icon :name="AddIcon" />
						</template>
						Add widget
					</n-button>
				</div>
			</div>

			<n-empty v-if="!form.panels.length" description="No widgets yet — add at least one" class="py-6" />

			<div v-else class="flex flex-col gap-2">
				<CardEntity
					v-for="(panel, index) of form.panels"
					:key="`${panel.id || panel.title}-${index}`"
					size="small"
				>
					<template #headerMain>{{ panel.title }}</template>
					<template #headerExtra>
						<div class="flex flex-wrap gap-2">
							<Badge type="splitted">
								<template #label>Type</template>
								<template #value>{{ panel.type }}</template>
							</Badge>
							<Badge type="splitted">
								<template #label>Width</template>
								<template #value>{{ panel.w }}/12</template>
							</Badge>
						</div>
					</template>
					<template #default>
						<div class="text-secondary flex flex-col gap-1 text-xs">
							<span>Filter: {{ panel.lucene || "*" }}</span>
							<span v-if="panel.field">Field: {{ panel.field }}</span>
							<span v-if="panel.fields?.length">Columns: {{ panel.fields.join(", ") }}</span>
						</div>
					</template>
					<template #footerExtra>
						<div class="flex flex-wrap gap-1">
							<n-button size="small" quaternary :disabled="index === 0" @click="movePanel(index, -1)">
								<template #icon>
									<Icon :name="UpIcon" />
								</template>
							</n-button>
							<n-button
								size="small"
								quaternary
								:disabled="index === form.panels.length - 1"
								@click="movePanel(index, 1)"
							>
								<template #icon>
									<Icon :name="DownIcon" />
								</template>
							</n-button>
							<n-button size="small" quaternary @click="duplicatePanel(index)">
								<template #icon>
									<Icon :name="DuplicateIcon" />
								</template>
							</n-button>
							<n-button size="small" quaternary @click="openPanelForm(index)">Edit</n-button>
							<n-button size="small" quaternary type="error" @click="removePanel(index)">Remove</n-button>
						</div>
					</template>
				</CardEntity>
			</div>
		</div>

		<!-- ── Preview + save ───────────────────────────────────── -->
		<div class="flex flex-wrap items-end gap-3">
			<n-form-item label="Preview against" :show-feedback="false" class="min-w-60 grow">
				<n-select
					v-model:value="previewEventSourceId"
					:options="eventSourceOptions"
					placeholder="Select an event source"
					clearable
				/>
			</n-form-item>
			<n-button :disabled="!canPreview" @click="showPreview = true">
				<template #icon>
					<Icon :name="PreviewIcon" />
				</template>
				Preview
			</n-button>
		</div>

		<div class="flex justify-between gap-4">
			<n-button @click="emit('close')">Cancel</n-button>
			<n-button type="primary" :disabled="!isValid" :loading="saving" @click="save()">
				{{ editing ? "Save changes" : "Create dashboard" }}
			</n-button>
		</div>

		<!-- ── Widget form ──────────────────────────────────────── -->
		<n-modal
			v-model:show="showPanelForm"
			preset="card"
			:title="editingPanelIndex === null ? 'Add widget' : 'Edit widget'"
			class="max-w-[95vw]"
			:style="{ width: '640px' }"
			:bordered="false"
			segmented
		>
			<CustomPanelForm
				:key="`panel-form-${editingPanelIndex ?? 'new'}`"
				:panel="editingPanelIndex === null ? null : form.panels[editingPanelIndex]"
				:field-options
				:loading-fields
				@submit="applyPanel"
				@close="showPanelForm = false"
			/>
		</n-modal>

		<!-- ── JSON import ──────────────────────────────────────── -->
		<n-modal
			v-model:show="showImport"
			preset="card"
			title="Load dashboard JSON"
			class="max-w-[95vw]"
			:style="{ width: '720px' }"
			:bordered="false"
			segmented
		>
			<div class="flex flex-col gap-4">
				<p class="text-secondary text-sm">
					Paste (or upload) a dashboard definition exported from CoPilot. It fills in the form below — nothing
					is saved until you submit.
				</p>
				<n-upload :show-file-list="false" accept=".json,application/json" :custom-request="readUploadedFile">
					<n-button size="small">
						<template #icon>
							<Icon :name="ImportIcon" />
						</template>
						Choose file
					</n-button>
				</n-upload>
				<n-input
					v-model:value="importText"
					type="textarea"
					:autosize="{ minRows: 8, maxRows: 18 }"
					placeholder="{'title': '...', 'panels': [ ... ] }"
					class="font-mono"
				/>
				<div class="flex justify-between gap-4">
					<n-button @click="showImport = false">Cancel</n-button>
					<n-button type="primary" :disabled="!importText.trim()" @click="applyImport()">Load</n-button>
				</div>
			</div>
		</n-modal>

		<!-- ── Live preview ─────────────────────────────────────── -->
		<n-modal
			v-model:show="showPreview"
			preset="card"
			title="Preview"
			class="max-w-[95vw]"
			:style="{ width: '1100px' }"
			:bordered="false"
			segmented
		>
			<CustomDashboardPreview
				v-if="showPreview && previewEventSourceId"
				:event-source-id="previewEventSourceId"
				:panels="form.panels"
				:default-query="form.default_query"
			/>
		</n-modal>
	</div>
</template>

<script setup lang="ts">
import type { UploadCustomRequestOptions } from "naive-ui"
import type { ApiError } from "@/types/common"
import type {
	CustomDashboard,
	CustomDashboardDefinition,
	CustomDashboardPanel,
	DashboardPanelType
} from "@/types/dashboards"
import type { EventSource } from "@/types/event-sources"
import {
	NButton,
	NCheckbox,
	NColorPicker,
	NDynamicTags,
	NEmpty,
	NFormItem,
	NInput,
	NModal,
	NSelect,
	NUpload,
	useMessage
} from "naive-ui"
import { computed, reactive, ref, watch } from "vue"
import Api from "@/api"
import Badge from "@/components/common/Badge.vue"
import CardEntity from "@/components/common/cards/CardEntity.vue"
import Icon from "@/components/common/Icon.vue"
import { getApiErrorMessage } from "@/utils"
import CustomDashboardPreview from "./CustomDashboardPreview.vue"
import CustomPanelForm from "./CustomPanelForm.vue"

const { customerCode, eventSourcesList, editing } = defineProps<{
	customerCode: string | null
	eventSourcesList: EventSource[]
	/** Template being edited; omitted when creating a new one. */
	editing?: CustomDashboard | null
}>()

const emit = defineEmits<{
	close: []
	saved: []
}>()

const AddIcon = "carbon:add"
const ImportIcon = "carbon:document-import"
const ExportIcon = "carbon:document-export"
const PreviewIcon = "carbon:view"
const UpIcon = "carbon:arrow-up"
const DownIcon = "carbon:arrow-down"
const DuplicateIcon = "carbon:copy"

const message = useMessage()

const eventTypeOptions = ["EDR", "EPP", "Cloud Integration", "Network Security", "Custom"].map(value => ({
	label: value,
	value
}))

// Same keys `getDashboardIcon()` maps to a real icon.
const iconOptions = ["dashboard", "cpu", "network", "storage", "security", "performance"].map(value => ({
	label: value,
	value
}))

const form = reactive<{
	title: string
	description: string
	vendor: string
	product: string
	event_type: string
	tags: string[]
	color: string
	icon: string
	default_query: string
	panels: CustomDashboardPanel[]
}>({
	title: editing?.title || "",
	description: editing?.description || "",
	vendor: editing?.vendor || "Custom",
	product: editing?.product || "",
	event_type: editing?.event_type || "Custom",
	tags: [...(editing?.tags || [])],
	color: editing?.color || "#38bdf8",
	icon: editing?.icon || "dashboard",
	default_query: editing?.default_query || "*",
	panels: (editing?.panels || []).map(panel => ({ ...panel }))
})

const shareGlobally = ref(editing ? editing.customer_code === null : false)
const saving = ref(false)

const showPanelForm = ref(false)
const editingPanelIndex = ref<number | null>(null)
const showImport = ref(false)
const importText = ref("")
const showPreview = ref(false)
const previewEventSourceId = ref<number | null>(null)

const eventSourceOptions = computed(() =>
	eventSourcesList
		.filter(source => source.enabled)
		.map(source => ({ label: `${source.name} (${source.event_type})`, value: source.id }))
)

const canPreview = computed(() => !!previewEventSourceId.value && !!form.panels.length)
const isValid = computed(() => !!form.title.trim() && !!form.panels.length)

// ── Field suggestions for the widget form ───────────────────────
const fieldOptions = ref<{ label: string; value: string }[]>([])
const loadingFields = ref(false)

function loadFieldMappings(eventSourceId: number | null) {
	const source = eventSourcesList.find(item => item.id === eventSourceId)
	if (!source || !customerCode) {
		fieldOptions.value = []
		return
	}

	loadingFields.value = true

	Api.siem
		.getFieldMappings(customerCode, source.name)
		.then(res => {
			if (res.data.success) {
				fieldOptions.value = (res.data.fields || []).map(field => ({
					label: `${field.field} · ${field.type}`,
					value: field.field
				}))
			}
		})
		.catch(() => {
			// Suggestions are a convenience — the field inputs stay free-text.
			fieldOptions.value = []
		})
		.finally(() => {
			loadingFields.value = false
		})
}

watch(previewEventSourceId, id => loadFieldMappings(id))

// Preselect the only source, so field suggestions work without extra clicks.
watch(
	() => eventSourceOptions.value,
	options => {
		if (!previewEventSourceId.value && options.length === 1) {
			previewEventSourceId.value = options[0].value
		}
	},
	{ immediate: true }
)

// ── Panels ──────────────────────────────────────────────────────
function openPanelForm(index: number | null) {
	editingPanelIndex.value = index
	showPanelForm.value = true
}

function applyPanel(panel: CustomDashboardPanel) {
	if (editingPanelIndex.value === null) {
		form.panels.push(panel)
	} else {
		form.panels[editingPanelIndex.value] = panel
	}
	showPanelForm.value = false
}

function removePanel(index: number) {
	form.panels.splice(index, 1)
}

function duplicatePanel(index: number) {
	const source = form.panels[index]
	// Drop the id: a copy must not collide with the panel it was cloned from.
	form.panels.splice(index + 1, 0, { ...source, id: undefined, title: `${source.title} (copy)` })
}

function movePanel(index: number, delta: number) {
	const target = index + delta
	if (target < 0 || target >= form.panels.length) return
	const [panel] = form.panels.splice(index, 1)
	form.panels.splice(target, 0, panel)
}

// ── Import / export ─────────────────────────────────────────────
function buildDefinition(): CustomDashboardDefinition {
	return {
		title: form.title.trim(),
		description: form.description.trim(),
		vendor: form.vendor.trim() || "Custom",
		product: form.product.trim(),
		event_type: form.event_type || "Custom",
		tags: form.tags,
		color: form.color,
		icon: form.icon,
		default_query: form.default_query.trim() || "*",
		panels: form.panels
	}
}

function exportDefinition() {
	const definition: CustomDashboardDefinition = {
		...buildDefinition(),
		template_key: editing?.template_key || null
	}
	const blob = new Blob([JSON.stringify(definition, null, 2)], { type: "application/json" })
	const url = URL.createObjectURL(blob)
	const link = document.createElement("a")
	link.href = url
	link.download = `${editing?.template_key || definition.title.toLowerCase().replaceAll(/\W+/g, "_") || "dashboard"}.json`
	link.click()
	URL.revokeObjectURL(url)
}

function readUploadedFile({ file, onFinish, onError }: UploadCustomRequestOptions) {
	const rawFile = file.file
	if (!rawFile) {
		onError()
		return
	}

	rawFile
		.text()
		.then(text => {
			importText.value = text
			onFinish()
		})
		.catch(() => {
			message.error("Could not read the selected file")
			onError()
		})
}

function applyImport() {
	let parsed: Partial<CustomDashboardDefinition>

	try {
		parsed = JSON.parse(importText.value)
	} catch {
		message.error("The provided text is not valid JSON")
		return
	}

	if (!parsed || !Array.isArray(parsed.panels) || !parsed.panels.length) {
		message.error("The definition must contain at least one panel")
		return
	}

	form.title = parsed.title || form.title
	form.description = parsed.description || ""
	form.vendor = parsed.vendor || "Custom"
	form.product = parsed.product || ""
	form.event_type = parsed.event_type || "Custom"
	form.tags = parsed.tags || []
	form.color = parsed.color || "#38bdf8"
	form.icon = parsed.icon || "dashboard"
	form.default_query = parsed.default_query || "*"
	form.panels = parsed.panels.map(panel => ({
		...panel,
		type: panel.type as DashboardPanelType,
		lucene: panel.lucene || "*",
		w: panel.w || 4,
		h: panel.h || 300
	}))

	showImport.value = false
	importText.value = ""
	message.success("Definition loaded — review it and save")
}

// ── Save ────────────────────────────────────────────────────────
function save() {
	if (!isValid.value) return

	saving.value = true
	const definition = buildDefinition()
	// A template is either scoped to the customer it was created for, or shared
	// with everyone; there is no "some customers" middle ground.
	const scopedCustomerCode = shareGlobally.value ? null : customerCode

	const request = editing
		? Api.siem.updateCustomDashboard(editing.template_key, {
				...definition,
				customer_code: scopedCustomerCode,
				share_globally: shareGlobally.value
			})
		: Api.siem.createCustomDashboard({ ...definition, customer_code: scopedCustomerCode })

	request
		.then(res => {
			if (res.data.success) {
				message.success(res.data?.message || "Custom dashboard saved successfully")
				emit("saved")
			} else {
				message.warning(res.data?.message || "An error occurred. Please try again later.")
			}
		})
		.catch(err => {
			message.error(getApiErrorMessage(err as ApiError) || "An error occurred. Please try again later.")
		})
		.finally(() => {
			saving.value = false
		})
}
</script>
