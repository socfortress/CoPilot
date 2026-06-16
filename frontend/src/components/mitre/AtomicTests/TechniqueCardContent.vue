<template>
	<div class="active-response-details">
		<n-spin :show="loading" class="min-h-48">
			<template v-if="content">
				<Markdown :source="content" />
			</template>
			<template v-else>
				<n-empty v-if="!loading" description="No description found" class="h-48 justify-center" />
			</template>
		</n-spin>
	</div>
</template>

<script setup lang="ts">
import type { ApiError } from "@/types/common"
import { NEmpty, NSpin, useMessage } from "naive-ui"
import { onBeforeMount, ref } from "vue"

import Api from "@/api"
import Markdown from "@/components/common/Markdown.vue"
import { getApiErrorMessage } from "@/utils"

const { techniqueId } = defineProps<{
	techniqueId: string
}>()

const message = useMessage()
const loading = ref(false)
const content = ref<string>()

function getContent() {
	loading.value = true

	Api.wazuh.mitre
		.getMitreAtomicTestContent(techniqueId)
		.then(res => {
			if (res.data.success) {
				content.value = res.data?.markdown_content
			} else {
				message.warning(res.data?.message || "An error occurred. Please try again later.")
			}
		})
		.catch(err => {
			message.error(getApiErrorMessage(err as ApiError) || "An error occurred. Please try again later.")
		})
		.finally(() => {
			loading.value = false
		})
}

onBeforeMount(() => {
	getContent()
})
</script>
