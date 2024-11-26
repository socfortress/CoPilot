<template>
	<n-input-group>
		<n-select
			v-model:value="templateName"
			:options="templateNameOptions"
			placeholder="Select..."
			clearable
			:loading="loadingOptions"
			class="overflow-hidden"
			to="body"
		/>
		<n-button secondary @click="(showManagerDialog = true)">
			<template #icon>
				<Icon :name="SettingsIcon" />
			</template>
		</n-button>
	</n-input-group>

	<n-modal
		v-model:show="showManagerDialog"
		display-directive="show"
		preset="card"
		:style="{ maxWidth: 'min(600px, 90vw)', minHeight: 'min(270px, 90vh)', overflow: 'hidden' }"
		title="Report templates manager"
		:bordered="false"
		segmented
	>
		<CaseReportTemplateManager />
	</n-modal>
</template>

<script setup lang="ts">
import Icon from "@/components/common/Icon.vue"
import { useCaseReportTemplateStore } from "@/stores/caseReportTemplate"
import { NButton, NInputGroup, NModal, NSelect } from "naive-ui"
import { computed, onBeforeMount, ref } from "vue"
import CaseReportTemplateManager from "./CaseReportTemplateManager.vue"

const templateName = defineModel<string | null>("value", { default: null })

const SettingsIcon = "carbon:settings"
const showManagerDialog = ref(false)
const caseReportTemplateStore = useCaseReportTemplateStore()
const loadingOptions = computed(() => caseReportTemplateStore.loading)
const templateNameList = computed(() => caseReportTemplateStore.templatesList)
const templateNameOptions = computed(() => templateNameList.value.map(item => ({ label: item, value: item })))

onBeforeMount(() => {
	caseReportTemplateStore.init()
})
</script>
