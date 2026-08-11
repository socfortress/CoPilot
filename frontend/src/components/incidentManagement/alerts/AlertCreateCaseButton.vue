<template>
	<n-button secondary type="primary" :loading="creating" @click="openDialog()">
		<template #icon>
			<Icon :name="DangerIcon" />
		</template>
		Create case
	</n-button>

	<n-modal
		v-model:show="showDialog"
		display-directive="show"
		preset="card"
		title="Create case from alert"
		:style="{ maxWidth: 'min(760px, 90vw)', minHeight: 'min(420px, 90vh)', maxHeight: '85vh' }"
		content-class="flex flex-col overflow-hidden px-2! py-0!"
		segmented
	>
		<n-scrollbar class="flex grow flex-col" content-class="grow" trigger="none">
			<div class="flex flex-col gap-4 px-5 py-5">
				<p class="text-secondary text-sm">
					Ranked against this alert's tags, MITRE techniques, rule groups and source. Pick one to apply its
					tasks on creation, or skip and let CoPilot auto-select as before.
				</p>

				<CaseTemplateSuggestions
					:alert-id="alert.id"
					:selected-template-id="selectedTemplate?.id ?? null"
					@select="selectedTemplate = $event"
				>
					<template #browseAll>
						<n-button text size="tiny" :focusable="false" @click="browseAllTemplates()">
							<template #icon>
								<Icon name="carbon:launch" />
							</template>
							Browse all templates
						</n-button>
					</template>
				</CaseTemplateSuggestions>
			</div>
		</n-scrollbar>

		<template #footer>
			<div class="flex flex-wrap items-center justify-between gap-3">
				<!--
					Omitting template_id is NOT "no template" — the backend then
					runs its own auto-apply selection. Labelled accordingly so
					the analyst isn't surprised by tasks appearing on a case they
					thought they'd created bare.
				-->
				<n-button secondary :disabled="creating" @click="createCase(null)">Skip — auto-select</n-button>

				<n-button type="primary" :loading="creating" :disabled="!selectedTemplate" @click="createCase()">
					<template #icon>
						<Icon :name="DangerIcon" />
					</template>
					Create with {{ selectedTemplate ? `"${truncatedName}"` : "template" }}
				</n-button>
			</div>
		</template>
	</n-modal>
</template>

<script setup lang="ts">
import type { ApiError } from "@/types/common"
import type { Alert } from "@/types/incidentManagement/alerts"
import type { CaseTemplate } from "@/types/incidentManagement/case-templates"
import { NButton, NModal, NScrollbar, useMessage } from "naive-ui"
import { computed, ref, toRefs } from "vue"
import Api from "@/api"
import Icon from "@/components/common/Icon.vue"
import CaseTemplateSuggestions from "@/components/incidentManagement/caseTemplates/CaseTemplateSuggestions.vue"
import { useNavigation } from "@/composables/useNavigation"
import { getApiErrorMessage } from "@/utils"

const props = defineProps<{ alert: Alert }>()
const emit = defineEmits<{
	(e: "updated", value: Alert): void
}>()

const { alert } = toRefs(props)

const DangerIcon = "majesticons:exclamation-line"

const message = useMessage()
const { routeIncidentManagementCaseTemplates } = useNavigation()
const creating = ref(false)
const showDialog = ref(false)
const selectedTemplate = ref<CaseTemplate | null>(null)

const truncatedName = computed(() => {
	const name = selectedTemplate.value?.name ?? ""
	return name.length > 28 ? `${name.slice(0, 27)}…` : name
})

function openDialog() {
	selectedTemplate.value = null
	showDialog.value = true
}

function browseAllTemplates() {
	// Full-page navigation, so close the modal first — leaving it mounted over
	// the templates list is the classic "back button does nothing" bug.
	showDialog.value = false
	routeIncidentManagementCaseTemplates().navigate()
}

function updateAlert(updatedAlert: Alert) {
	emit("updated", updatedAlert)
}

/**
 * `template` explicitly null means "skip" — send no template_id and let the
 * backend's own auto-apply selection run, which is exactly what this button
 * did before suggestions existed. Passing undefined falls back to whatever the
 * analyst selected in the panel.
 */
function createCase(template: CaseTemplate | null | undefined = undefined) {
	const chosen = template === undefined ? selectedTemplate.value : template
	creating.value = true

	const params: Record<string, number> = {}
	if (chosen) params.template_id = chosen.id

	Api.incidentManagement.cases
		.createCaseFromAlert(alert.value.id, params)
		.then(res => {
			if (res.data.success) {
				updateAlert({
					...alert.value,
					linked_cases: [
						{
							id: res.data.case_alert_link.case_id,
							case_name: "",
							case_description: "",
							case_creation_time: new Date(),
							assigned_to: null,
							case_status: null,
							customer_code: null,
							comments: []
						}
					]
				})
				showDialog.value = false
				message.success(res.data?.message || "Case created successfully")
			} else {
				message.warning(res.data?.message || "An error occurred. Please try again later.")
			}
		})
		.catch(err => {
			message.error(getApiErrorMessage(err as ApiError) || "An error occurred. Please try again later.")
		})
		.finally(() => {
			creating.value = false
		})
}
</script>
