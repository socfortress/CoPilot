<template>
	<div ref="page" class="page">
		<div class="section flex justify-end gap-3 lg:justify-between">
			<div class="left-box hidden gap-3 lg:flex">
				<StackProvisioningButton size="small" type="primary" />
				<CloudSecurityAssessmentButton size="small" type="primary" />
				<WebVulnerabilityAssessmentButton size="small" type="primary" />
			</div>
			<div class="right-box hidden gap-3 lg:flex">
				<ActiveResponseWizardButton size="small" type="primary" />
				<ThreatIntelButton size="small" type="primary" />
			</div>
			<div class="mobile-box block lg:hidden">
				<n-button size="small" type="primary" @click="showQuickActions = true">
					<template #icon>
						<Icon :name="QuickActionsIcon"></Icon>
					</template>
					Quick Actions
				</n-button>
			</div>
		</div>
		<div class="section">
			<div class="grid grid-flow-row-dense grid-cols-12 gap-6">
				<div class="xs:col-span-12 col-span-12 sm:col-span-4 lg:col-span-2">
					<AgentsCard class="h-full" />
				</div>
				<div class="xs:col-span-6 col-span-12 sm:col-span-4 lg:col-span-2">
					<HealthcheckCard class="h-full" />
				</div>
				<div class="xs:col-span-6 col-span-12 sm:col-span-4 lg:col-span-2">
					<CustomersCard class="h-full" />
				</div>
				<div class="col-span-12 lg:col-span-3">
					<IncidentAlerts class="h-full" />
				</div>
				<div class="col-span-12 lg:col-span-3">
					<IncidentCases class="h-full" />
				</div>
			</div>
		</div>
		<div class="section">
			<IndicesMarquee @click="gotoIndex($event.index)" />
		</div>
		<div class="section">
			<div class="columns flex-col lg:flex-row">
				<div class="col basis-1/2">
					<ClusterHealth class="stretchy" />
				</div>
				<div class="col basis-1/2">
					<NodeAllocation class="stretchy" />
				</div>
			</div>
		</div>
		<div class="section">
			<PipeList @open-rule="gotoGraylogPipelines($event)" />
		</div>

		<n-drawer
			v-model:show="showQuickActions"
			:width="300"
			style="max-width: 90vw"
			:trap-focus="false"
			display-directive="show"
		>
			<n-drawer-content title="Quick Actions" closable :native-scrollbar="false">
				<div class="flex flex-col gap-3">
					<StackProvisioningButton size="small" type="primary" />
					<CloudSecurityAssessmentButton size="small" type="primary" />
					<WebVulnerabilityAssessmentButton size="small" type="primary" />
					<ActiveResponseWizardButton size="small" type="primary" />
					<ThreatIntelButton size="small" type="primary" />
				</div>
			</n-drawer-content>
		</n-drawer>
	</div>
</template>

<script setup lang="ts">
import ActiveResponseWizardButton from "@/components/activeResponse/ActiveResponseWizardButton.vue"
import CloudSecurityAssessmentButton from "@/components/cloudSecurityAssessment/CloudSecurityAssessmentButton.vue"
import Icon from "@/components/common/Icon.vue"
import PipeList from "@/components/graylog/Pipelines/PipeList.vue"
import ClusterHealth from "@/components/indices/ClusterHealth.vue"
import IndicesMarquee from "@/components/indices/Marquee.vue"
import NodeAllocation from "@/components/indices/NodeAllocation.vue"
import AgentsCard from "@/components/overview/AgentsCard.vue"
import CustomersCard from "@/components/overview/CustomersCard.vue"
import HealthcheckCard from "@/components/overview/HealthcheckCard.vue"
import IncidentAlerts from "@/components/overview/IncidentAlerts.vue"
import IncidentCases from "@/components/overview/IncidentCases.vue"
import StackProvisioningButton from "@/components/stackProvisioning/StackProvisioningButton.vue"
import WebVulnerabilityAssessmentButton from "@/components/webVulnerabilityAssessment/WebVulnerabilityAssessmentButton.vue"
import { useGoto } from "@/composables/useGoto"
import { useResizeObserver } from "@vueuse/core"
import { NButton, NDrawer, NDrawerContent } from "naive-ui"
import { defineAsyncComponent, ref } from "vue"

const ThreatIntelButton = defineAsyncComponent(() => import("@/components/threatIntel/ThreatIntelButton.vue"))

const QuickActionsIcon = "ant-design:thunderbolt-outlined"
const page = ref()
const cardDirection = ref<"horizontal" | "vertical">("horizontal")
const showQuickActions = ref(false)
const { gotoIndex, gotoGraylogPipelines } = useGoto()

useResizeObserver(page, entries => {
	const entry = entries[0]
	const { width } = entry.contentRect

	cardDirection.value = width > 500 ? "horizontal" : "vertical"
})
</script>

<style lang="scss" scoped>
.page {
	.section {
		@apply mb-6;

		.columns {
			display: flex;
			@apply gap-6;

			.stretchy {
				height: 100%;
			}
		}
	}
}
</style>
