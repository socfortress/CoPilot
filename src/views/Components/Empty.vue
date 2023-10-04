<template>
	<div class="page">
		<div class="page-header">
			<div class="title">Empty</div>
			<div class="links">
				<a
					href="https://www.naiveui.com/en-US/light/components/empty"
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
				<n-empty description="You can't find anything">
					<template #extra>
						<n-button size="small">Find Something New</n-button>
					</template>
				</n-empty>
				<template #code="{ html }">
					{{ html(`
					<n-empty description="You can't find anything">
						<template #extra>
							<n-button size="small">Find Something New</n-button>
						</template>
					</n-empty>
					`) }}
				</template>
			</CardCodeExample>
		</div>
	</div>
</template>

<script lang="ts" setup>
import { NIcon, NEmpty, NButton } from "naive-ui"
import ExternalIcon from "@vicons/tabler/ExternalLink"
</script>
