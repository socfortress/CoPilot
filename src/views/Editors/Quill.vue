<template>
	<div class="page">
		<div class="page-header">
			<div class="title">Quill</div>
			<div class="links">
				<a
					href="https://vueup.github.io/vue-quill/"
					target="_blank"
					alt="docs"
					rel="nofollow noopener noreferrer"
				>
					<Icon :name="ExternalIcon" :size="16" />
					docs
				</a>
			</div>
		</div>

		<n-card>
			<QuillEditor
				v-if="mounted"
				theme="snow"
				toolbar="minimal"
				@blur="resetScroll()"
				style="width: 100%; height: 60vh"
			/>
		</n-card>
	</div>
</template>

<script setup lang="ts">
import { NCard } from "naive-ui"
import { ref, defineAsyncComponent, type Component, onMounted } from "vue"

import Icon from "@/components/common/Icon.vue"
const ExternalIcon = "tabler:external-link"

import "@/assets/scss/quill-override.scss"

const mounted = ref(false)

const QuillEditor = defineAsyncComponent<Component>(() => {
	return (async () => {
		const { QuillEditor } = await import("@vueup/vue-quill")
		return QuillEditor
	})()
})

function resetScroll() {
	window.scrollTo(0, 0)
}

onMounted(() => {
	mounted.value = true
})
</script>
