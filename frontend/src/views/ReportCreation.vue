<template>
	<div class="page page-wrapped page-without-footer flex flex-col gap-5">
		<ReportWizard
			v-if="licenseResponse"
			hide-panels-select
			class="animate-fade"
			@timerange="timerange = $event"
			@organization="org = $event"
			@dashboard="dashboard = $event"
			@panels="panels = $event"
		/>

		<ReportPanels
			v-if="licenseResponse"
			:timerange="timerange"
			:org="org"
			:dashboard="dashboard"
			:panels="panels"
			class="animate-fade"
		/>

		<div v-if="licenseResponse" class="over-layer mobile-layer">
			<n-alert>
				<template #icon>
					<Icon :name="AlertIcon" :size="18"></Icon>
				</template>
				This function is available only for desktop devices
			</n-alert>
		</div>

		<LicenseFeatureCheck
			feature="REPORTING"
			feedback="overlay"
			@response="licenseResponse = $event"
			@start-loading="licenseChecking = true"
			@stop-loading="licenseChecking = false"
		/>

		<n-spin v-if="licenseChecking" class="min-h-52"></n-spin>
	</div>
</template>

<script setup lang="ts">
import type { ReportTimeRange } from "@/api/endpoints/reporting"
import type { Dashboard, Org, Panel } from "@/types/reporting.d"
import { NAlert, NSpin } from "naive-ui"
import { ref } from "vue"
import Icon from "@/components/common/Icon.vue"
import LicenseFeatureCheck from "@/components/license/LicenseFeatureCheck.vue"
import ReportPanels from "@/components/reportCreation/Panels.vue"
import ReportWizard from "@/components/reportCreation/Wizard.vue"

const AlertIcon = "mdi:alert-outline"
const timerange = ref<ReportTimeRange | null>(null)
const org = ref<Org | null>(null)
const dashboard = ref<Dashboard | null>(null)
const panels = ref<Panel[]>([])
const licenseChecking = ref(false)
const licenseResponse = ref(false)
</script>

<style lang="scss" scoped>
@import "../app-layouts/HorizontalNav/_variables.scss";

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
