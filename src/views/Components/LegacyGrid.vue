<template>
	<div class="page">
		<div class="page-header">
			<div class="title">Legacy Grid</div>
			<div class="links">
				<a
					href="https://www.naiveui.com/en-US/light/components/legacy-grid"
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
				<n-row :gutter="[12, 8]">
					<n-col :span="6">
						<div class="light-green" />
					</n-col>
					<n-col :span="6">
						<div class="green" />
					</n-col>
					<n-col :span="6">
						<div class="light-green" />
					</n-col>
					<n-col :span="6">
						<div class="green" />
					</n-col>
					<n-col :span="6">
						<div class="light-green" />
					</n-col>
					<n-col :span="6">
						<div class="green" />
					</n-col>
					<n-col :span="6">
						<div class="light-green" />
					</n-col>
					<n-col :span="6">
						<div class="green" />
					</n-col>
				</n-row>
				<template #code="{ html, css }">
					{{ html(`
					<n-row :gutter="[12, 8]">
						<n-col :span="6">
							<div class="light-green" />
						</n-col>
						<n-col :span="6">
							<div class="green" />
						</n-col>
						<n-col :span="6">
							<div class="light-green" />
						</n-col>
						<n-col :span="6">
							<div class="green" />
						</n-col>
						<n-col :span="6">
							<div class="light-green" />
						</n-col>
						<n-col :span="6">
							<div class="green" />
						</n-col>
						<n-col :span="6">
							<div class="light-green" />
						</n-col>
						<n-col :span="6">
							<div class="green" />
						</n-col>
					</n-row>
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
import { NRow, NCol } from "naive-ui"
import Icon from "@/components/common/Icon.vue"
const ExternalIcon = "tabler:external-link"
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
