<template>
	<n-modal
		v-model:show="showLocal"
		preset="card"
		display-directive="show"
		:title="entry ? `Import — ${entry.name}` : 'Import library entry'"
		:style="{ maxWidth: 'min(640px, 92vw)' }"
		segmented
	>
		<template v-if="entry">
			<div class="flex flex-col gap-3">
				<n-alert v-if="!result" type="info" :show-icon="false">
					This will create a new
					<strong>global</strong>
					case template (no customer or source scope). If you want a customer-specific version,
					edit the template after import.
				</n-alert>

				<div v-if="!result" class="flex flex-col gap-3">
					<div class="grid grid-cols-2 gap-2">
						<div class="info-cell">
							<div class="info-label">Key</div>
							<code class="text-xs">{{ entry.key }}</code>
						</div>
						<div class="info-cell">
							<div class="info-label">Source</div>
							<code v-if="entry.source" class="text-xs">{{ entry.source }}</code>
							<span v-else class="text-tertiary text-xs">—</span>
						</div>
					</div>

					<div v-if="entry.description" class="text-secondary text-sm">
						{{ entry.description }}
					</div>

					<div class="flex flex-col gap-2">
						<div class="text-secondary text-xs uppercase tracking-wide">
							Tasks ({{ entry.tasks.length }})
						</div>
						<div class="task-list">
							<div
								v-for="(t, idx) of entry.tasks"
								:key="`${entry.key}-${idx}`"
								class="task-row"
							>
								<div class="task-index">{{ t.order_index }}</div>
								<div class="flex min-w-0 flex-col gap-1">
									<div class="flex items-center gap-2">
										<div class="task-title">{{ t.title }}</div>
										<Badge v-if="t.mandatory" color="warning" size="small">
											<template #value>mandatory</template>
										</Badge>
									</div>
									<div v-if="t.description" class="text-secondary text-xs">
										{{ t.description }}
									</div>
								</div>
							</div>
						</div>
					</div>

					<div class="flex justify-end gap-2">
						<n-button size="small" quaternary :disabled="submitting" @click="close">
							Cancel
						</n-button>
						<n-button size="small" type="primary" :loading="submitting" @click="submit">
							Import as global template
						</n-button>
					</div>
				</div>

				<!-- Success view -->
				<div v-else class="flex flex-col gap-3">
					<n-alert type="success" :show-icon="false">
						<template #header>Template imported</template>
						<div class="text-sm">
							<strong>{{ result.name }}</strong>
							is now in your Templates list. You can apply it to any case from the case
							detail page, or edit/customize it from the Templates tab.
						</div>
					</n-alert>
					<div class="flex justify-end">
						<n-button size="small" type="primary" @click="close">Done</n-button>
					</div>
				</div>
			</div>
		</template>
	</n-modal>
</template>

<script setup lang="ts">
import type {
	CaseTemplate,
	CaseTemplateLibraryEntry
} from "@/types/incidentManagement/caseTemplates.d"
import { NAlert, NButton, NModal, useMessage } from "naive-ui"
import { computed, ref, watch } from "vue"
import Api from "@/api"
import Badge from "@/components/common/Badge.vue"

const props = defineProps<{
	show: boolean
	entry: CaseTemplateLibraryEntry | null
}>()

const emit = defineEmits<{
	(e: "update:show", value: boolean): void
	(e: "imported", template: CaseTemplate): void
}>()

const message = useMessage()

const showLocal = computed({
	get: () => props.show,
	set: v => emit("update:show", v)
})

const submitting = ref(false)
const result = ref<CaseTemplate | null>(null)

async function submit() {
	if (!props.entry) return
	submitting.value = true
	try {
		const res = await Api.incidentManagement.caseTemplates.importLibraryEntry(props.entry.key)
		if (res.data?.success && res.data.template) {
			result.value = res.data.template
			emit("imported", res.data.template)
			message.success(`Imported '${res.data.template.name}'`)
		} else {
			message.warning(res.data?.message || "Failed to import library entry")
		}
	} catch (err: any) {
		// Backend returns HTTP 409 on name collision with a useful detail message.
		const status = err.response?.status
		const detail =
			err.response?.data?.detail ||
			err.response?.data?.message ||
			err.message ||
			"Failed to import library entry"
		if (status === 409) {
			message.warning(detail)
		} else {
			message.error(detail)
		}
	} finally {
		submitting.value = false
	}
}

function close() {
	showLocal.value = false
}

// Reset result whenever the modal opens fresh OR the selected entry changes.
watch(
	() => [props.show, props.entry?.key] as const,
	([open]) => {
		if (open) result.value = null
	}
)
</script>

<style scoped lang="scss">
.info-cell {
	display: flex;
	flex-direction: column;
	gap: 4px;
	padding: 8px 10px;
	background: var(--bg-secondary-color);
	border: 1px solid var(--border-color);
	border-radius: var(--border-radius);
}
.info-label {
	font-size: 0.7rem;
	text-transform: uppercase;
	letter-spacing: 0.04em;
	color: var(--fg-tertiary-color);
}

.task-list {
	display: flex;
	flex-direction: column;
	border: 1px solid var(--border-color);
	border-radius: var(--border-radius);
	background: var(--bg-default-color);
	max-height: 320px;
	overflow-y: auto;
}
.task-row {
	display: flex;
	align-items: flex-start;
	gap: 10px;
	padding: 8px 12px;
}
.task-row + .task-row {
	border-top: 1px solid var(--border-color);
}
.task-index {
	font-family: var(--font-family-mono, monospace);
	font-size: 0.75rem;
	color: var(--fg-tertiary-color);
	min-width: 22px;
	text-align: right;
	padding-top: 2px;
}
.task-title {
	font-size: 0.85rem;
	color: var(--fg-default-color);
}
</style>
