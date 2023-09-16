<template>
	<div class="page page-wrapped flex flex-col">
		<div class="page-header">
			<div class="title">Tiptap</div>
			<div class="links">
				<a
					href="https://tiptap.dev/installation/vue3"
					target="_blank"
					alt="docs"
					rel="nofollow noopener noreferrer"
					class="ml-4"
				>
					<n-icon :size="16">
						<ExternalIcon />
					</n-icon>
					docs
				</a>
			</div>
		</div>

		<div class="grow overflow-hidden editor-wrap">
			<Tiptap v-model="text" class="h-full" />
		</div>
	</div>
</template>

<script setup lang="ts">
import { NIcon } from "naive-ui"
import ExternalIcon from "@vicons/tabler/ExternalLink"
import Tiptap from "@/components/editors/Tiptap"
import { ref } from "vue"

const text = ref("<p>I’m running Tiptap with Vue.js. 🎉</p>")
</script>

<style scoped lang="scss">
.editor-wrap {
	background-color: var(--bg-color);
	border-radius: var(--border-radius);
}
</style>
