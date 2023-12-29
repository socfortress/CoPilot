<template>
	<div class="page">
		<div class="section">
			<div class="columns">
				<CardStats title="Total Agents" :value="99999" horizontal>
					<template #icon>
						<CardStatsIcon
							:iconName="ErrorIcon"
							boxed
							:boxSize="50"
							:color="style['--secondary4-color']"
						></CardStatsIcon>
					</template>
				</CardStats>
				<CardStats title="Online Agents" :value="99999" horizontal>
					<template #icon>
						<CardStatsIcon
							:iconName="ErrorIcon"
							boxed
							:boxSize="50"
							:color="style['--secondary4-color']"
						></CardStatsIcon>
					</template>
				</CardStats>
				<CardStats title="SOC Alerts" :value="99999" horizontal>
					<template #icon>
						<CardStatsIcon
							:iconName="ErrorIcon"
							boxed
							:boxSize="50"
							:color="style['--secondary4-color']"
						></CardStatsIcon>
					</template>
				</CardStats>
				<CardStats title="Customers" :value="99999" horizontal>
					<template #icon>
						<CardStatsIcon
							:iconName="ErrorIcon"
							boxed
							:boxSize="50"
							:color="style['--secondary4-color']"
						></CardStatsIcon>
					</template>
				</CardStats>
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
import CardStats from "@/components/common/CardStats.vue"
import CardStatsIcon from "@/components/common/CardStatsIcon.vue"
import type { IndexStats } from "@/types/indices.d"
import { useThemeStore } from "@/stores/theme"

const router = useRouter()
const style = computed<{ [key: string]: any }>(() => useThemeStore().style)

const ErrorIcon = "carbon:sailboat-offshore"

function gotoIndicesPage(index: IndexStats) {
	router.push(`/indices?index_name=${index.index}`).catch(() => {})
}
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
