<template>
	<div class="page" ref="page">
		<div class="section justify-end sm:justify-between flex gap-3">
			<div class="left-box hidden sm:flex gap-3">
				<StackProvisioningButton size="small" type="primary" />
			</div>
			<div class="right-box hidden sm:flex gap-3">
				<ActiveResponseWizardButton size="small" type="primary" />
				<ThreatIntelButton size="small" type="primary" />
			</div>
			<div class="mobile-box block sm:hidden">
				<n-button size="small" type="primary" @click="showQuickActions = true">
					<template #icon><Icon :name="QuickActionsIcon"></Icon></template>
					Quick Actions
				</n-button>
			</div>
		</div>
		<div class="section">
			<div class="columns column-800 overflow-hidden">
				<div class="basis-2/5">
					<AgentsCard />
				</div>
				<div class="basis-2/5">
					<HealthcheckCard />
				</div>
				<div class="basis-1/5 flex gap-6">
					<!--
						<div class="grow overflow-hidden">
							<SocAlertsCard class="h-full" :vertical="cardDirection === 'vertical'" />
						</div>
					-->
					<div class="grow overflow-hidden">
						<CustomersCard class="h-full" :vertical="cardDirection === 'vertical'" />
					</div>
				</div>
			</div>
		</div>
		<div class="section">
			<IndicesMarquee @click="gotoIndicesPage" />
		</div>
		<div class="section">
			<div class="columns">
				<div class="col basis-1/2">
					<ClusterHealth class="stretchy" />
				</div>
				<div class="col basis-1/2">
					<NodeAllocation class="stretchy" />
				</div>
			</div>
		</div>
		<div class="section">
			<PipeList minHeight="28px" @open-rule="gotoPipelinesPage($event)" />
		</div>

		<n-drawer
			v-model:show="showQuickActions"
			:width="250"
			style="max-width: 90vw"
			:trap-focus="false"
			display-directive="show"
		>
			<n-drawer-content title="Quick Actions" closable :native-scrollbar="false">
				<div class="flex flex-col gap-3">
					<StackProvisioningButton size="small" type="primary" />
					<ActiveResponseWizardButton size="small" type="primary" />
					<ThreatIntelButton size="small" type="primary" />
				</div>
			</n-drawer-content>
		</n-drawer>
	</div>
</template>

<script setup lang="ts">
import { ref } from "vue"
import { NButton, NDrawer, NDrawerContent } from "naive-ui"
import { useRouter } from "vue-router"
import ClusterHealth from "@/components/indices/ClusterHealth.vue"
import NodeAllocation from "@/components/indices/NodeAllocation.vue"
import IndicesMarquee from "@/components/indices/Marquee.vue"
import ThreatIntelButton from "@/components/alerts/ThreatIntelButton.vue"
import ActiveResponseWizardButton from "@/components/activeResponse/ActiveResponseWizardButton.vue"
import StackProvisioningButton from "@/components/stackProvisioning/StackProvisioningButton.vue"
import AgentsCard from "@/components/overview/AgentsCard.vue"
import HealthcheckCard from "@/components/overview/HealthcheckCard.vue"
// import SocAlertsCard from "@/components/overview/SocAlertsCard.vue"
import CustomersCard from "@/components/overview/CustomersCard.vue"
import PipeList from "@/components/graylog/Pipelines/PipeList.vue"
import type { IndexStats } from "@/types/indices.d"
import { useResizeObserver } from "@vueuse/core"
import Icon from "@/components/common/Icon.vue"

const QuickActionsIcon = "ant-design:thunderbolt-outlined"
const router = useRouter()
const page = ref()
const cardDirection = ref<"horizontal" | "vertical">("horizontal")
const showQuickActions = ref(false)

function gotoIndicesPage(index: IndexStats) {
	router.push({ name: "Indices", query: { index_name: index.index } })
}

function gotoPipelinesPage(rule: string) {
	router.push({ name: "Graylog-Pipelines", query: { rule } })
}

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

	@media (max-width: 1000px) {
		.section {
			.columns {
				&:not(.column-1200, .column-800) {
					flex-direction: column;
				}
			}
		}
	}
	@media (max-width: 800px) {
		.section {
			.columns.column-800 {
				flex-direction: column;
			}
		}
	}
	@media (max-width: 1200px) {
		.section {
			.columns.column-1200 {
				flex-direction: column;
			}
		}
	}
}
</style>
