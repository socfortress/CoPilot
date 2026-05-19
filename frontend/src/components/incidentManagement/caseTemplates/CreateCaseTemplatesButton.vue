<template>
	<div>
		<n-button size="small" secondary type="primary" @click="openCreate">
			<template #icon><Icon name="carbon:add" /></template>
			New template
		</n-button>

		<n-modal
			v-model:show="showEditor"
			preset="card"
			title="New template"
			display-directive="show"
			style="max-width: 720px"
		>
			<CaseTemplateEditor @saved="handleSuccess" @cancel="handleCancel" />
		</n-modal>
	</div>
</template>

<script setup lang="tsx">
import type { CaseTemplate } from "@/types/incidentManagement/caseTemplates.d"
import { NButton, NModal } from "naive-ui"
import { ref } from "vue"
import Icon from "@/components/common/Icon.vue"
import CaseTemplateEditor from "./CaseTemplateEditor.vue"

const emit = defineEmits<{
	(e: "success", template: CaseTemplate): void
	(e: "cancel"): void
}>()

const showEditor = ref(false)
const editing = ref<CaseTemplate | null>(null)

function handleSuccess(template: CaseTemplate) {
	showEditor.value = false
	emit("success", template)
}

function handleCancel() {
	showEditor.value = false
	emit("cancel")
}

function openCreate() {
	editing.value = null
	showEditor.value = true
}
</script>
