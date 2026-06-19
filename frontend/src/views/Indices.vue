<template>
	<div class="flex flex-col">
		<div class="mb-6">
			<IndicesMarquee :indices @click="setIndex" />
		</div>

		<div class="mb-6">
			<Details v-model="currentIndex" :indices />
		</div>

		<div class="mb-6">
			<div class="flex gap-6 max-[1000px]:flex-col">
				<div class="basis-1/2">
					<ClusterHealth class="h-full" />
				</div>
				<div class="basis-1/2">
					<UnhealthyIndices :indices class="h-full" @click="setIndex" />
				</div>
			</div>
		</div>

		<div class="mb-6">
			<CustomerIndicesSize @click="setIndex" />
		</div>

		<n-card class="mb-6 overflow-hidden" content-class="p-0!">
			<div class="flex gap-0! max-[1200px]:flex-col">
				<div class="basis-2/5">
					<NodeAllocation class="h-full rounded-none" :bordered="false" />
				</div>
				<div class="basis-3/5 overflow-hidden">
					<TopIndices :indices class="rounded-none" :bordered="false" />
				</div>
			</div>
		</n-card>
	</div>
</template>

<script lang="ts" setup>
import type { ApiError } from "@/types/common"
import type { IndexStats } from "@/types/indices.d"
import { NCard, useMessage } from "naive-ui"
import { defineAsyncComponent, onBeforeMount, ref } from "vue"
import { useRoute } from "vue-router"
import Api from "@/api"
import ClusterHealth from "@/components/indices/ClusterHealth.vue"
import CustomerIndicesSize from "@/components/indices/CustomerIndicesSize.vue"
import Details from "@/components/indices/Details.vue"
import IndicesMarquee from "@/components/indices/Marquee.vue"
import NodeAllocation from "@/components/indices/NodeAllocation.vue"
import UnhealthyIndices from "@/components/indices/UnhealthyIndices.vue"
import { getApiErrorMessage } from "@/utils"

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
					getApiErrorMessage(err as ApiError) ||
						"Wazuh-Indexer returned Unauthorized. Please check your connector credentials."
				)
			} else if (err.response?.status === 404) {
				message.error(getApiErrorMessage(err as ApiError) || "No indices were found.")
			} else {
				message.error(getApiErrorMessage(err as ApiError) || "An error occurred. Please try again later.")
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
