<template>
	<div class="page">
		<div class="section">
			<IndicesMarquee :indices="indices" @click="setIndex" />
		</div>

		<div class="section">
			<Details v-model="currentIndex" :indices="indices" />
		</div>

		<div class="section">
			<div class="columns flex">
				<div class="col basis-1/2">
					<ClusterHealth class="stretchy" />
				</div>
				<div class="col basis-1/2">
					<UnhealthyIndices :indices="indices" class="stretchy" @click="setIndex" />
				</div>
			</div>
		</div>

		<n-card class="section overflow-hidden" content-style="padding:0">
			<div class="columns column-1200 flex gap-0!">
				<div class="col basis-2/5">
					<NodeAllocation class="stretchy" style="border-radius: 0" :bordered="false" />
				</div>
				<div class="col basis-3/5 overflow-hidden">
					<TopIndices :indices="indices" style="border-radius: 0" :bordered="false" />
				</div>
			</div>
		</n-card>
	</div>
</template>

<script lang="ts" setup>
import type { IndexStats } from "@/types/indices.d"
import { NCard, useMessage } from "naive-ui"
import { defineAsyncComponent, onBeforeMount, ref } from "vue"
import { useRoute } from "vue-router"
import Api from "@/api"
import ClusterHealth from "@/components/indices/ClusterHealth.vue"
import Details from "@/components/indices/Details.vue"
import IndicesMarquee from "@/components/indices/Marquee.vue"
import NodeAllocation from "@/components/indices/NodeAllocation.vue"
import UnhealthyIndices from "@/components/indices/UnhealthyIndices.vue"

const TopIndices = defineAsyncComponent(() => import("@/components/indices/TopIndices.vue"))

const message = useMessage()
const route = useRoute()
const indices = ref<IndexStats[] | null>(null)
const loadingIndex = ref(false)
const currentIndex = ref<IndexStats | null>(null)
const requestedIndex = ref<string | null>(null)

function setIndex(index: IndexStats | string) {
	if (typeof index === "string") {
		const indexStats = indices.value?.find(o => o.index === index) || null
		indexStats && (currentIndex.value = indexStats)
	} else {
		currentIndex.value = index
	}
}

function getIndices(cb?: () => void) {
	loadingIndex.value = true

	Api.wazuh.indices
		.getIndices()
		.then(res => {
			if (res.data.success) {
				indices.value = res.data.indices_stats

				if (cb) cb()
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
				message.error(err.response?.data?.message || "No indices were found.")
			} else {
				message.error(err.response?.data?.message || "An error occurred. Please try again later.")
			}
		})
		.finally(() => {
			loadingIndex.value = false
		})
}

onBeforeMount(() => {
	if (route.query?.index_name) {
		requestedIndex.value = route.query.index_name.toString()
	}

	getIndices(() => {
		requestedIndex.value && setIndex(requestedIndex.value)
	})
})
</script>

<style lang="scss" scoped>
.page {
	.section {
		margin-bottom: calc(var(--spacing) * 6);

		.columns {
			display: flex;
			gap: calc(var(--spacing) * 6);

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
