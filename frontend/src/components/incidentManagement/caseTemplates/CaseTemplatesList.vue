<template>
	<div>
		<n-tabs v-model:value="activeTab" type="line" animated>
			<n-tab-pane name="templates" tab="Templates">
				<CaseTemplatesTable ref="templatesTableRef" />
			</n-tab-pane>

			<n-tab-pane name="library" tab="Library">
				<CaseTemplatesLibrary @imported="onLibraryImported" />
			</n-tab-pane>

			<template #suffix>
				<CreateCaseTemplatesButton @success="onTemplateSaved" />
			</template>
		</n-tabs>
	</div>
</template>

<script setup lang="tsx">
import { NTabPane, NTabs } from "naive-ui"
import { ref } from "vue"
import CaseTemplatesLibrary from "./CaseTemplatesLibrary.vue"
import CaseTemplatesTable from "./CaseTemplatesTable.vue"
import CreateCaseTemplatesButton from "./CreateCaseTemplatesButton.vue"

const templatesTableRef = ref<InstanceType<typeof CaseTemplatesTable>>()

const activeTab = ref<"templates" | "library">("templates")

function onTemplateSaved() {
	templatesTableRef.value?.fetchTemplates()
}

function onLibraryImported() {
	// After a library import lands, jump the user back to the Templates tab and
	// refetch so the freshly-imported row appears immediately.
	activeTab.value = "templates"
	templatesTableRef.value?.fetchTemplates()
}
</script>
