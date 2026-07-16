<template>
	<div class="page flex flex-col gap-4">
		<DetailPageHeader :title="template?.name" :back-route="routeIncidentManagementCaseTemplates()">
			<template v-if="template" #meta>
				<span class="text-secondary font-mono text-sm">#{{ template.id }}</span>
			</template>
		</DetailPageHeader>

		<n-spin v-if="templateId != null" :show="loading" class="min-h-40">
			<CaseTemplateEditor
				v-if="template"
				:key="template.id"
				:template
				deletable
				@saved="onSaved($event)"
				@cancel="goBack(routeIncidentManagementCaseTemplates())"
				@deleted="onDeleted()"
			/>
		</n-spin>
		<n-empty v-else description="Invalid template ID" class="h-48 justify-center" />
	</div>
</template>

<script setup lang="ts">
import type { CaseTemplate } from "@/types/incidentManagement/case-templates"
import { NEmpty, NSpin, useMessage } from "naive-ui"
import Api from "@/api"
import DetailPageHeader from "@/components/common/DetailPageHeader.vue"
import CaseTemplateEditor from "@/components/incidentManagement/caseTemplates/CaseTemplateEditor.vue"
import { useEntityDetails } from "@/composables/useEntityDetails"
import { useNavigation, useRouteIdParam } from "@/composables/useNavigation"

const { goBack, routeIncidentManagementCaseTemplates } = useNavigation()

const message = useMessage()

const templateId = useRouteIdParam("id")

const {
	loading,
	entity: template,
	reload
} = useEntityDetails<CaseTemplate, number>({
	entity: () => null,
	id: () => templateId.value,
	// the endpoint takes no abort signal, so the request itself is not cancellable
	fetch: id =>
		Api.incidentManagement.caseTemplates.getTemplate(id).then(res => ({
			entity: res.data.success ? (res.data.template ?? null) : null,
			message: res.data.message
		})),
	notFoundMessage: "Template not found",
	errorMessage: "Failed to load template"
})

function onSaved(saved: CaseTemplate) {
	message.success(`Saved "${saved.name}"`)
	// task edits are streamed by the editor itself — refetch so the page shows server truth
	reload()
}

function onDeleted() {
	routeIncidentManagementCaseTemplates().replace()
}
</script>
