<template>
	<n-modal
		v-model:show="show"
		preset="card"
		display-directive="show"
		:title="entry ? `Import — ${entry.name}` : 'Import library entry'"
		:style="{ maxWidth: 'min(640px, 92vw)' }"
		segmented
	>
		<template v-if="entry">
			<div class="flex flex-col gap-3">
				<n-alert v-if="!result" type="info" :show-icon="false">
					<div class="text-sm">
						This will create a new
						<strong>global</strong>
						case template (no customer or source scope). If you want a customer-specific version, edit the
						template after import.
					</div>
				</n-alert>

				<div v-if="!result" class="flex flex-col gap-3">
					<div class="grid grid-cols-2 gap-3">
						<CardKV>
							<template #key>Key</template>
							<template #value>
								{{ entry.key }}
							</template>
						</CardKV>
						<CardKV>
							<template #key>Source</template>
							<template #value>
								<span v-if="entry.source">{{ entry.source }}</span>
								<span v-else class="text-secondary">—</span>
							</template>
						</CardKV>
					</div>

					<CardKV v-if="entry.match_field && entry.match_value">
						<template #key>Conditional auto-apply</template>
						<template #value>
							Only fires when
							<code>{{ entry.match_field }}</code>
							==
							<code>{{ entry.match_value }}</code>
							on the originating Wazuh document.
						</template>
					</CardKV>

					<CardKV v-if="entry.description">
						<template #key>Description</template>
						<template #value>
							{{ entry.description }}
						</template>
					</CardKV>

					<CardKV value-class="flex flex-col divide-y divide-border p-0!">
						<template #key>Tasks ({{ entry.tasks.length }})</template>
						<template #value>
							<div
								v-for="(t, idx) of entry.tasks"
								:key="`${entry.key}-${idx}`"
								class="flex items-center gap-4 px-4 py-2"
							>
								<div class="text-secondary font-mono">{{ t.order_index }}</div>
								<div class="flex min-w-0 flex-col gap-0.5">
									<div class="flex items-center gap-2">
										<div class="font-medium">{{ t.title }}</div>
										<Badge v-if="t.mandatory" color="warning" size="small">
											<template #value>mandatory</template>
										</Badge>
									</div>
									<div v-if="t.description" class="text-secondary text-xs">
										{{ t.description }}
									</div>
								</div>
							</div>
						</template>
					</CardKV>

					<div class="flex justify-end gap-2">
						<n-button size="small" quaternary :disabled="submitting" @click="close">Cancel</n-button>
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
							is now in your Templates list. You can apply it to any case from the case detail page, or
							edit/customize it from the Templates tab.
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
import type { ApiError } from "@/types/common"
import type { CaseTemplate, CaseTemplateLibraryEntry } from "@/types/incidentManagement/caseTemplates.d"
import { NAlert, NButton, NModal, useMessage } from "naive-ui"
import { ref, watch } from "vue"
import Api from "@/api"
import Badge from "@/components/common/Badge.vue"
import CardKV from "@/components/common/cards/CardKV.vue"
import { getApiErrorMessage } from "@/utils"

const props = defineProps<{
	entry: CaseTemplateLibraryEntry | null
}>()

const emit = defineEmits<{
	(e: "imported", template: CaseTemplate): void
}>()

const message = useMessage()

const show = defineModel<boolean>("show", { required: true, default: false })

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
	} catch (err) {
		// Backend returns HTTP 409 on name collision with a useful detail message.
		const status = err.response?.status
		const detail = getApiErrorMessage(err as ApiError) || "Failed to import library entry"
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
	show.value = false
}

// Reset result whenever the modal opens fresh OR the selected entry changes.
watch([show.value, () => props.entry?.key], ([open]) => {
	if (open) result.value = null
})
</script>
