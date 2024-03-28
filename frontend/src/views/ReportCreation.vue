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
		<div class="mobile-overlay">
			<div>
				<Icon :name="AlertIcon" :size="18" class="relative top-0.5 mr-1"></Icon>
				This function is available only for desktop devices
			</div>
		</div>
	</div>
</template>

<script setup lang="ts">
import { ref } from "vue"
import ReportWizard from "@/components/reportCreation/Wizard.vue"
import ReportPanels from "@/components/reportCreation/Panels.vue"
import type { Dashboard, Org, Panel } from "@/types/reporting.d"
import type { ReportTimeRange } from "@/api/reporting"
import Icon from "@/components/common/Icon.vue"

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

	.mobile-overlay {
		background-color: rgba(var(--bg-body-rgb), 0.8);
		position: absolute;
		top: 0;
		left: 0;
		right: 0;
		bottom: 0;
		display: flex;
		align-items: center;
		justify-content: center;
		padding: 40px;
		text-align: center;
		font-size: 20px;
		display: none;

		@media (max-width: $sidebar-bp) {
			display: flex;
		}
	}
}
</style>
