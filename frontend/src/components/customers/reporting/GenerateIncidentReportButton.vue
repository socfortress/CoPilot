<template>
	<n-button type="primary" :secondary :size @click="showModal = true">
		<template #icon>
			<Icon :name="AddIcon" />
		</template>
		Generate Report
	</n-button>

	<n-modal
		v-model:show="showModal"
		preset="card"
		title="Generate Incident Management Report"
		class="max-w-160!"
		display-directive="show"
		closable
	>
		<GenerateIncidentReportForm
			:customer-code
			:default-template
			@generated="handleGenerated"
			@cancel="showModal = false"
		/>
	</n-modal>
</template>

<script setup lang="ts">
import type { IncidentReportGeneratedPayload, IncidentReportTemplate } from "@/types/incidentReports"
import { NButton, NModal } from "naive-ui"
import { ref } from "vue"
import Icon from "@/components/common/Icon.vue"
import GenerateIncidentReportForm from "./GenerateIncidentReportForm.vue"

defineProps<{
	customerCode?: string
	defaultTemplate?: IncidentReportTemplate
	size?: "tiny" | "small" | "medium" | "large"
	secondary?: boolean
}>()

const emit = defineEmits<{
	generated: [payload: IncidentReportGeneratedPayload]
}>()

const AddIcon = "carbon:document-add"
const showModal = ref(false)

function handleGenerated(payload: IncidentReportGeneratedPayload) {
	showModal.value = false
	emit("generated", payload)
}
</script>
