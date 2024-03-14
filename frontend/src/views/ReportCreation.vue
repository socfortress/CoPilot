<template>
	<div class="page page-wrapped page-without-footer flex flex-col gap-4">
		<ReportWizard
			@organization="org = $event"
			@dashboard="dashboard = $event"
			@panels="panels = $event"
			hide-panels-select
		/>
		<ReportPanels :org="org" :dashboard="dashboard" :panels="panels" />
	</div>
</template>

<script setup lang="ts">
import { ref } from "vue"
import ReportWizard from "@/components/reportCreation/Wizard.vue"
import ReportPanels from "@/components/reportCreation/Panels.vue"
import type { Dashboard, Org, Panel } from "@/types/reporting"

const org = ref<Org | null>(null)
const dashboard = ref<Dashboard | null>(null)
const panels = ref<Panel[]>([])
</script>

<style lang="scss" scoped>
.page {
	overflow: hidden;
}
</style>
