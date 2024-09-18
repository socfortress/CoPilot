<template>
	<div class="active-response-details">
		<n-spin :show="loadingActiveResponse" class="min-h-48">
			<template v-if="activeResponseDetails?.markdown_content">
				<Suspense>
					<Markdown :source="activeResponseDetails.markdown_content" />
				</Suspense>
			</template>
			<template v-else>
				<n-empty v-if="!loadingActiveResponse" description="No description found" class="justify-center h-48" />
			</template>
		</n-spin>
	</div>
</template>

<script setup lang="ts">
import type { ActiveResponseDetails, SupportedActiveResponse } from "@/types/activeResponse.d"
import Api from "@/api"
import { NEmpty, NSpin, useMessage } from "naive-ui"
import { defineAsyncComponent, onBeforeMount, ref } from "vue"

const { activeResponse } = defineProps<{
	activeResponse: SupportedActiveResponse
}>()

const Markdown = defineAsyncComponent(() => import("@/components/common/Markdown.vue"))

const message = useMessage()
const loadingActiveResponse = ref(false)
const activeResponseDetails = ref<ActiveResponseDetails>()

function getAvailableIntegrations() {
	loadingActiveResponse.value = true

	Api.activeResponse
		.getDetails(activeResponse.name)
		.then(res => {
			if (res.data.success) {
				activeResponseDetails.value = res.data?.active_response
			} else {
				message.warning(res.data?.message || "An error occurred. Please try again later.")
			}
		})
		.catch(err => {
			message.error(err.response?.data?.message || "An error occurred. Please try again later.")
		})
		.finally(() => {
			loadingActiveResponse.value = false
		})
}

onBeforeMount(() => {
	getAvailableIntegrations()
})
</script>
