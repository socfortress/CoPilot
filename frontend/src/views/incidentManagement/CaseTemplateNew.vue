<template>
	<div class="page flex flex-col gap-4">
		<div class="flex min-w-0 items-center gap-4">
			<n-button quaternary class="shrink-0" @click="goBack(routeIncidentManagementCaseTemplates())">
				<template #icon>
					<Icon :name="BackIcon" />
				</template>
				Back
			</n-button>

			<span class="truncate text-lg font-semibold">New template</span>
		</div>

		<CaseTemplateEditor @saved="onSaved($event)" @cancel="goBack(routeIncidentManagementCaseTemplates())" />
	</div>
</template>

<script setup lang="ts">
import type { CaseTemplate } from "@/types/incidentManagement/case-templates"
import { NButton, useMessage } from "naive-ui"
import Icon from "@/components/common/Icon.vue"
import CaseTemplateEditor from "@/components/incidentManagement/caseTemplates/CaseTemplateEditor.vue"
import { useNavigation } from "@/composables/useNavigation"

const { goBack, routeIncidentManagementCaseTemplates, routeIncidentManagementCaseTemplate } = useNavigation()

const BackIcon = "carbon:arrow-left"
const message = useMessage()

function onSaved(saved: CaseTemplate) {
	message.success(`Created "${saved.name}"`)
	// land on the template we just created rather than back on an empty form
	routeIncidentManagementCaseTemplate(saved.id).replace()
}
</script>
