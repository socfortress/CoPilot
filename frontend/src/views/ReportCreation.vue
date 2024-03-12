<template>
	<div class="page">
		<ReportWizard
			@updated="setPanels($event)"
			@updateAvailable="setAvailable($event)"
			hide-generate-button
			hide-panels
		/>
		<ReportPanels :panels-list="panelsList" :available-panels="availablePanels" class="mt-5" />
	</div>
</template>

<script setup lang="ts">
import { ref } from "vue"
import ReportWizard from "@/components/reportCreation/Wizard.vue"
import ReportPanels from "@/components/reportCreation/Panels.vue"
import type { Panel } from "@/types/reporting"

const panelsList = ref<Panel[]>([])
const availablePanels = ref<Panel[]>([])

function setPanels(panels: Panel[]) {
	panelsList.value = panels
}

function setAvailable(panels: Panel[]) {
	availablePanels.value = panels
}
</script>
