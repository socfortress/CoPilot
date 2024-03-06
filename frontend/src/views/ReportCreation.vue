<template>
	<div class="page">
		<ReportWizard @updated="setPanels($event)" hide-generate-button />
		<ReportPanels :panels-list="panelsList" class="mt-5" />
	</div>
</template>

<script setup lang="ts">
import { ref } from "vue"
import ReportWizard from "@/components/reportCreation/Wizard.vue"
import ReportPanels from "@/components/reportCreation/Panels.vue"
import type { Panel } from "@/types/reporting"

const panelsList = ref<Panel[]>([])

function setPanels(panels: Panel[]) {
	panelsList.value = panels
}
</script>
