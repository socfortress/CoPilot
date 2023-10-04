<template>
	<div class="page">
		<div class="page-header">
			<div class="title">Pagination</div>
			<div class="links">
				<a
					href="https://www.naiveui.com/en-US/light/components/pagination"
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
				<n-space vertical>
					<n-pagination
						v-model:page="page"
						:page-count="100"
						size="small"
						show-quick-jumper
						show-size-picker
					/>
					<n-pagination
						v-model:page="page"
						:page-count="100"
						size="medium"
						show-quick-jumper
						show-size-picker
					/>
					<n-pagination
						v-model:page="page"
						:page-count="100"
						size="large"
						show-quick-jumper
						show-size-picker
					/>
				</n-space>
				<template #code="{ html, js }">
					{{ html(`
					<n-space vertical>
						<n-pagination
							v-model:page="page"
							:page-count="100"
							size="small"
							show-quick-jumper
							show-size-picker
						/>
						<n-pagination
							v-model:page="page"
							:page-count="100"
							size="medium"
							show-quick-jumper
							show-size-picker
						/>
						<n-pagination
							v-model:page="page"
							:page-count="100"
							size="large"
							show-quick-jumper
							show-size-picker
						/>
					</n-space>
					`) }}

					{{ js(`const page = ref(2)`) }}
				</template>
			</CardCodeExample>
		</div>
	</div>
</template>

<script lang="ts" setup>
import { NIcon, NSpace, NPagination } from "naive-ui"
import ExternalIcon from "@vicons/tabler/ExternalLink"
import { ref } from "vue"

const page = ref(2)
</script>
