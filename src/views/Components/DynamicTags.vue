<template>
	<div class="page">
		<div class="page-header">
			<div class="title">Dynamic Tags</div>
			<div class="links">
				<a
					href="https://www.naiveui.com/en-US/light/components/dynamic-tags"
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

		<div class="components-list">
			<CardCodeExample title="Basic">
				<n-dynamic-tags v-model:value="tags" />
				<template #code="{ html, js }">
					{{ html(`
					<n-dynamic-tags v-model:value="tags" />
					`) }}

					{{ js(`const tags = ref(["teacher", "programmer"])`) }}
				</template>
			</CardCodeExample>
		</div>
	</div>
</template>

<script lang="ts" setup>
import { NIcon, NDynamicTags } from "naive-ui"
import ExternalIcon from "@vicons/tabler/ExternalLink"
import { ref } from "vue"

const tags = ref(["teacher", "programmer"])
</script>
