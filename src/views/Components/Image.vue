<template>
	<div class="page">
		<div class="page-header">
			<div class="title">Image</div>
			<div class="links">
				<a
					href="https://www.naiveui.com/en-US/light/components/image"
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
				<n-image width="200" src="https://picsum.photos/seed/YbVNwOA/400/400" />
				<template #code="{ html }">
					{{ html(`
					<n-image width="200" src="https://picsum.photos/seed/YbVNwOA/400/400" />
					`) }}
				</template>
			</CardCodeExample>

			<CardCodeExample title="Image group">
				<n-image-group>
					<n-space>
						<n-image width="200" src="https://picsum.photos/seed/oXUVYK/400/400" />
						<n-image width="200" src="https://picsum.photos/seed/ip686sm/400/400" />
						<n-image width="200" src="https://picsum.photos/seed/mkf2nv/400/400" />
					</n-space>
				</n-image-group>
				<template #code="{ html }">
					{{ html(`
					<n-image-group>
						<n-space>
							<n-image width="200" src="https://picsum.photos/seed/oXUVYK/400/400" />
							<n-image width="200" src="https://picsum.photos/seed/ip686sm/400/400" />
							<n-image width="200" src="https://picsum.photos/seed/mkf2nv/400/400" />
						</n-space>
					</n-image-group>
					`) }}
				</template>
			</CardCodeExample>
		</div>
	</div>
</template>

<script lang="ts" setup>
import { NImage, NImageGroup, NSpace } from "naive-ui"
import Icon from "@/components/common/Icon.vue"
const ExternalIcon = "tabler:external-link"
</script>
