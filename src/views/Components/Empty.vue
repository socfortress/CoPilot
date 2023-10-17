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
				>
					<Icon :name="ExternalIcon" :size="16" />
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
import { NEmpty, NButton } from "naive-ui"
import Icon from "@/components/common/Icon.vue"
const ExternalIcon = "tabler:external-link"
</script>
