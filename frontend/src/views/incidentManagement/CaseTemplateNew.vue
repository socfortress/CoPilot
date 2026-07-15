<template>
	<div class="page flex flex-col gap-4">
		<DetailPageHeader title="New template" :back-route="routeIncidentManagementCaseTemplates()" />

		<CaseTemplateEditor @saved="onSaved($event)" @cancel="goBack(routeIncidentManagementCaseTemplates())" />
	</div>
</template>

<script setup lang="ts">
import type { CaseTemplate } from "@/types/incidentManagement/case-templates"
import { useMessage } from "naive-ui"
import DetailPageHeader from "@/components/common/DetailPageHeader.vue"
import CaseTemplateEditor from "@/components/incidentManagement/caseTemplates/CaseTemplateEditor.vue"
import { useNavigation } from "@/composables/useNavigation"

const { goBack, routeIncidentManagementCaseTemplates, routeIncidentManagementCaseTemplate } = useNavigation()

const message = useMessage()

function onSaved(saved: CaseTemplate) {
	message.success(`Created "${saved.name}"`)
	// land on the template we just created rather than back on an empty form
	routeIncidentManagementCaseTemplate(saved.id).replace()
}
</script>
