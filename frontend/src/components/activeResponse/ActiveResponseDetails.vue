<template>
	<div class="active-response-details">
		<n-spin :show="loadingActiveResponse" class="min-h-48">
			<template v-if="activeResponseDetails?.markdown_content">
				<Suspense>
					<Markdown :source="activeResponseDetails.markdown_content" />
				</Suspense>
			</template>
			<template v-else>
				<n-empty description="No description found" class="justify-center h-48" v-if="!loadingActiveResponse" />
			</template>
		</n-spin>
	</div>
</template>

<script setup lang="ts">
import { ref, onBeforeMount, defineAsyncComponent } from "vue"
import { useMessage, NSpin, NEmpty } from "naive-ui"
import Api from "@/api"
import type { ActiveResponseDetails, SupportedActiveResponse } from "@/types/activeResponse.d"
const Markdown = defineAsyncComponent(() => import("@/components/common/Markdown.vue"))

const { activeResponse } = defineProps<{
	activeResponse: SupportedActiveResponse
}>()

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
