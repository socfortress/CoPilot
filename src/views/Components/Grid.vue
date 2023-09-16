<template>
	<div class="page">
		<div class="page-header">
			<div class="title">Grid</div>
			<div class="links">
				<a
					href="https://www.naiveui.com/en-US/light/components/grid"
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
				<n-grid :x-gap="12" :y-gap="8" :cols="4">
					<n-grid-item>
						<div class="light-green" />
					</n-grid-item>
					<n-grid-item>
						<div class="green" />
					</n-grid-item>
					<n-grid-item>
						<div class="light-green" />
					</n-grid-item>
					<n-grid-item>
						<div class="green" />
					</n-grid-item>
					<n-grid-item>
						<div class="light-green" />
					</n-grid-item>
					<n-grid-item>
						<div class="green" />
					</n-grid-item>
					<n-grid-item>
						<div class="light-green" />
					</n-grid-item>
					<n-grid-item>
						<div class="green" />
					</n-grid-item>
				</n-grid>
				<template #code="{ html, css }">
					{{ html(`
					<n-grid :x-gap="12" :y-gap="8" :cols="4">
						<n-grid-item>
							<div class="light-green" />
						</n-grid-item>
						<n-grid-item>
							<div class="green" />
						</n-grid-item>
						<n-grid-item>
							<div class="light-green" />
						</n-grid-item>
						<n-grid-item>
							<div class="green" />
						</n-grid-item>
						<n-grid-item>
							<div class="light-green" />
						</n-grid-item>
						<n-grid-item>
							<div class="green" />
						</n-grid-item>
						<n-grid-item>
							<div class="light-green" />
						</n-grid-item>
						<n-grid-item>
							<div class="green" />
						</n-grid-item>
					</n-grid>
					`) }}

					{{
						css(`
						.light-green {
							height: 108px;
							background-color: rgba(0, 128, 0, 0.12);
						}
						.green {
							height: 108px;
							background-color: rgba(0, 128, 0, 0.24);
						}
						`)
					}}
				</template>
			</CardCodeExample>
		</div>
	</div>
</template>

<script lang="ts" setup>
import { NIcon, NGrid, NGridItem } from "naive-ui"
import ExternalIcon from "@vicons/tabler/ExternalLink"
</script>

<style scoped>
.light-green {
	height: 108px;
	background-color: rgba(0, 128, 0, 0.12);
}
.green {
	height: 108px;
	background-color: rgba(0, 128, 0, 0.24);
}
</style>
