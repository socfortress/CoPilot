<template>
	<el-scrollbar class="page page-indices">
		<div class="section">
			<IndicesMarquee :indices="indices" @click="setIndex" />
		</div>

		<div class="section">
			<Details :indices="indices" v-model="currentIndex" />
		</div>

		<div class="section">
			<div class="columns">
				<div class="col basis-50">
					<ClusterHealth class="stretchy" />
				</div>
				<div class="col basis-50">
					<UnhealthyIndices :indices="indices" @click="setIndex" class="stretchy" />
				</div>
			</div>
		</div>

		<div class="section">
			<div class="columns column-1200">
				<div class="col basis-40">
					<NodeAllocation class="stretchy" />
				</div>
				<div class="col basis-60 chart-card">
					<TopIndices :indices="indices" />
				</div>
			</div>
		</div>
	</el-scrollbar>
</template>

<script lang="ts" setup>
import { type Index } from "@/types/indices.d"
import Api from "@/api"
import { ElMessage } from "element-plus"
import { onBeforeMount, ref } from "vue"
import IndicesMarquee from "@/components/indices/Marquee.vue"
import NodeAllocation from "@/components/indices/NodeAllocation.vue"
import ClusterHealth from "@/components/indices/ClusterHealth.vue"
import Details from "@/components/indices/Details.vue"
import UnhealthyIndices from "@/components/indices/UnhealthyIndices.vue"
import TopIndices from "@/components/indices/TopIndices.vue"

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
				indices.value = res.data.indices
			} else {
				ElMessage({
					message: res.data?.message || "An error occurred. Please try again later.",
					type: "error"
				})
			}
		})
		.catch(err => {
			if (err.response.status === 401) {
				ElMessage({
					message:
						err.response?.data?.message ||
						"Wazuh-Indexer returned Unauthorized. Please check your connector credentials.",
					type: "error"
				})
			} else if (err.response.status === 404) {
				ElMessage({
					message: err.response?.data?.message || "No alerts were found.",
					type: "error"
				})
			} else {
				ElMessage({
					message: err.response?.data?.message || "An error occurred. Please try again later.",
					type: "error"
				})
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
@import "@/assets/scss/_variables";
@import "@/assets/scss/card-shadow";

.page-indices {
	.section {
		margin-bottom: var(--size-6);

		.columns {
			display: flex;
			gap: var(--size-6);

			.col {
				flex-grow: 1;
				//overflow: hidden;
				&.basis-20 {
					flex-basis: 20%;
				}
				&.basis-40 {
					flex-basis: 40%;
				}
				&.basis-50 {
					flex-basis: 50%;
				}
				&.basis-60 {
					flex-basis: 60%;
				}
				&.basis-80 {
					flex-basis: 80%;
				}

				&.chart-card {
				}
			}

			.stretchy {
				height: 100%;
				box-sizing: border-box;
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
