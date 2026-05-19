<template>
	<div>
		<n-tabs v-model:value="activeTab" type="line" animated>
			<n-tab-pane name="templates" tab="Templates">
				<CaseTemplatesTable ref="templatesTableRef" />
			</n-tab-pane>

			<n-tab-pane name="library" tab="Library">
				<CaseTemplatesLibrary @imported="reloadTemplates" />
			</n-tab-pane>

			<template #suffix>
				<CreateCaseTemplatesButton @success="reloadTemplates" />
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

function reloadTemplates() {
	activeTab.value = "templates"
	templatesTableRef.value?.fetchTemplates()
}
</script>
