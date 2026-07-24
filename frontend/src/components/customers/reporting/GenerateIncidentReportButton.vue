<template>
	<n-button type="primary" @click="showModal = true">
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
		<GenerateIncidentReportForm :customer-code @generated="handleGenerated" @cancel="showModal = false" />
	</n-modal>
</template>

<script setup lang="ts">
import { NButton, NModal } from "naive-ui"
import { ref } from "vue"
import Icon from "@/components/common/Icon.vue"
import GenerateIncidentReportForm from "./GenerateIncidentReportForm.vue"

defineProps<{
	customerCode: string
}>()

const emit = defineEmits<{
	generated: [reportId: number]
}>()

const AddIcon = "carbon:document-add"
const showModal = ref(false)

function handleGenerated(reportId: number) {
	showModal.value = false
	emit("generated", reportId)
}
</script>
