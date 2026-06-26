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
			class="max-w-180!"
		>
			<CaseTemplateEditor ref="editorRef" @saved="handleSuccess" @cancel="handleCancel" />
		</n-modal>
	</div>
</template>

<script setup lang="tsx">
import type { CaseTemplate } from "@/types/incidentManagement/case-templates"
import { NButton, NModal } from "naive-ui"
import { ref } from "vue"
import Icon from "@/components/common/Icon.vue"
import CaseTemplateEditor from "./CaseTemplateEditor.vue"

const emit = defineEmits<{
	(e: "success", template: CaseTemplate): void
	(e: "cancel"): void
}>()

const showEditor = ref(false)
const editorRef = ref<InstanceType<typeof CaseTemplateEditor>>()

function handleSuccess(template: CaseTemplate) {
	showEditor.value = false
	emit("success", template)
}

function handleCancel() {
	showEditor.value = false
	emit("cancel")
}

function openCreate() {
	showEditor.value = true
	editorRef.value?.validate()
}
</script>
