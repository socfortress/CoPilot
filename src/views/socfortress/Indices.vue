<template>
	<div class="page">
		<div class="section">
			<IndicesMarquee :indices="indices" @click="setIndex" />
		</div>

		<div class="section">
			<Details :indices="indices" v-model="currentIndex" />
		</div>

		<div class="section">
			<div class="columns flex">
				<div class="col basis-1/2">
					<ClusterHealth class="stretchy" />
				</div>
				<div class="col basis-1/2">
					<UnhealthyIndices :indices="indices" @click="setIndex" class="stretchy" />
				</div>
			</div>
		</div>

		<div class="section">
			<div class="columns flex column-1200">
				<div class="col basis-2/5">
					<NodeAllocation class="stretchy" />
				</div>
				<div class="col basis-3/5 overflow-hidden">
					<TopIndices :indices="indices" />
				</div>
			</div>
		</div>
	</div>
</template>

<script lang="ts" setup>
import { type Index } from "@/types/indices.d"
import Api from "@/api"
import { onBeforeMount, ref } from "vue"
import IndicesMarquee from "@/components/indices/Marquee.vue"
import NodeAllocation from "@/components/indices/NodeAllocation.vue"
import ClusterHealth from "@/components/indices/ClusterHealth.vue"
import Details from "@/components/indices/Details.vue"
import UnhealthyIndices from "@/components/indices/UnhealthyIndices.vue"
import TopIndices from "@/components/indices/TopIndices.vue"
import { useMessage } from "naive-ui"

const message = useMessage()
const indices = ref<Index[] | null>(null)
const loadingIndex = ref(false)
const currentIndex = ref<Index | null>(null)

function setIndex(index: Index) {
	currentIndex.value = index
}

function getIndices() {
	loadingIndex.value = true

	Api.indices
		.getIndices()
		.then(res => {
			if (res.data.success) {
				indices.value = res.data.indices_stats
			} else {
				message.error(res.data?.message || "An error occurred. Please try again later.")
			}
		})
		.catch(err => {
			if (err.response?.status === 401) {
				message.error(
					err.response?.data?.message ||
						"Wazuh-Indexer returned Unauthorized. Please check your connector credentials."
				)
			} else if (err.response?.status === 404) {
				message.error(err.response?.data?.message || "No alerts were found.")
			} else {
				message.error(err.response?.data?.message || "An error occurred. Please try again later.")
			}
		})
		.finally(() => {
			loadingIndex.value = false
		})
}

onBeforeMount(() => {
	getIndices()
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
