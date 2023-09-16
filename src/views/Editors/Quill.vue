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
					class="ml-4"
				>
					<n-icon :size="16">
						<ExternalIcon />
					</n-icon>
					docs
				</a>
			</div>
		</div>

		<n-card>
			<QuillEditor theme="snow" toolbar="minimal" @blur="resetScroll()" style="width: 100%; height: 60vh" />
		</n-card>
	</div>
</template>

<script setup lang="ts">
import { NIcon, NCard } from "naive-ui"
import ExternalIcon from "@vicons/tabler/ExternalLink"
import { QuillEditor } from "@vueup/vue-quill"
import "@/assets/scss/quill-override.scss"

function resetScroll() {
	window.scrollTo(0, 0)
}
</script>
