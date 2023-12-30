<template>
	<div class="page" ref="page">
		<div class="section">
			<div class="columns overflow-hidden">
				<div class="basis-1/3">
					<AgentsCard />
				</div>
				<div class="basis-1/3">
					<HealthcheckCard />
				</div>
				<div class="basis-1/3 flex gap-6">
					<div class="grow overflow-hidden">
						<SocAlertsCard class="h-full" :vertical="cardDirection === 'vertical'" />
					</div>
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
	</div>
</template>

<script setup lang="ts">
import { computed, onBeforeMount, ref } from "vue"
import { useRoute, useRouter } from "vue-router"
import ClusterHealth from "@/components/indices/ClusterHealth.vue"
import NodeAllocation from "@/components/indices/NodeAllocation.vue"
import IndicesMarquee from "@/components/indices/Marquee.vue"
import AgentsCard from "@/components/overview/AgentsCard.vue"
import HealthcheckCard from "@/components/overview/HealthcheckCard.vue"
import SocAlertsCard from "@/components/overview/SocAlertsCard.vue"
import CustomersCard from "@/components/overview/CustomersCard.vue"
import CardStats from "@/components/common/CardStats.vue"
import CardStatsIcon from "@/components/common/CardStatsIcon.vue"
import type { IndexStats } from "@/types/indices.d"
import { useThemeStore } from "@/stores/theme"
import { useResizeObserver } from "@vueuse/core"

const router = useRouter()
const style = computed<{ [key: string]: any }>(() => useThemeStore().style)
const page = ref()
const cardDirection = ref<"horizontal" | "vertical">("horizontal")

const ErrorIcon = "carbon:sailboat-offshore"
const OverviewIcon = "carbon:dashboard"
const IndiciesIcon = "ph:list-magnifying-glass"
const AgentsIcon = "carbon:network-3"
const ConnectorsIcon = "carbon:hybrid-networking"
const GraylogIcon = "majesticons:pulse-line"
const AlertsIcon = "carbon:warning-hex"
const ArtifactsIcon = "carbon:document-multiple-01"
const SOCIcon = "carbon:security"
const HealthcheckIcon = "ph:heartbeat"
const CustomersIcon = "carbon:user-multiple"
const LogsIcon = "carbon:cloud-logging"

function gotoIndicesPage(index: IndexStats) {
	router.push(`/indices?index_name=${index.index}`).catch(() => {})
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
