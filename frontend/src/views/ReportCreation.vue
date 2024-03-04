<template>
	<div class="page">
		<ReportWizard @generated="setLinks($event)" @reset="isDirty = true" />
		<ReportPanels :links-list="linksList" v-model:is-dirty="isDirty" class="mt-5" />
	</div>
</template>

<script setup lang="ts">
import { ref } from "vue"
import ReportWizard from "@/components/reportCreation/Wizard.vue"
import ReportPanels from "@/components/reportCreation/Panels.vue"
import type { PanelLink } from "@/types/reporting"

const linksList = ref<PanelLink[]>([])
const isDirty = ref<boolean>(false)

function setLinks(links: PanelLink[]) {
	linksList.value = links
	isDirty.value = false
}
</script>
