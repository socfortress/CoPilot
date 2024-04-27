<template>
	<div class="page page-wrapped page-without-footer flex flex-col gap-5">
		<ReportWizard
			@timerange="timerange = $event"
			@organization="org = $event"
			@dashboard="dashboard = $event"
			@panels="panels = $event"
			hide-panels-select
		/>
		<ReportPanels :timerange="timerange" :org="org" :dashboard="dashboard" :panels="panels" />
		<div class="over-layer mobile-layer">
			<n-alert>
				<template #icon>
					<Icon :name="AlertIcon" :size="18"></Icon>
				</template>
				This function is available only for desktop devices
			</n-alert>
		</div>
		<LicenseFeatureOverlay :feature="'REPORTING'" />
	</div>
</template>

<script setup lang="ts">
import { ref } from "vue"
import { NAlert } from "naive-ui"
import ReportWizard from "@/components/reportCreation/Wizard.vue"
import ReportPanels from "@/components/reportCreation/Panels.vue"
import type { Dashboard, Org, Panel } from "@/types/reporting.d"
import type { ReportTimeRange } from "@/api/reporting"
import Icon from "@/components/common/Icon.vue"
import LicenseFeatureOverlay from "@/components/license/LicenseFeatureOverlay.vue"

const AlertIcon = "mdi:alert-outline"

const timerange = ref<ReportTimeRange | null>(null)
const org = ref<Org | null>(null)
const dashboard = ref<Dashboard | null>(null)
const panels = ref<Panel[]>([])
</script>

<style lang="scss" scoped>
@import "../layouts/HorizontalNav/_variables.scss";

.page {
	overflow: hidden;
	position: relative;

	.mobile-layer {
		display: none;
		@media (max-width: $sidebar-bp) {
			display: flex;
		}
	}
}
</style>
