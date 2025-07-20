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
import { NEmpty, NSpin, useMessage } from "naive-ui"
import { defineAsyncComponent, onBeforeMount, ref } from "vue"
import Api from "@/api"

const { techniqueId } = defineProps<{
	techniqueId: string
}>()

const Markdown = defineAsyncComponent(() => import("@/components/common/Markdown.vue"))

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
			message.error(err.response?.data?.message || "An error occurred. Please try again later.")
		})
		.finally(() => {
			loading.value = false
		})
}

onBeforeMount(() => {
	getContent()
})
</script>
