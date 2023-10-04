<template>
	<div class="page">
		<div class="page-header">
			<div class="title">Color Picker</div>
			<div class="links">
				<a
					href="https://www.naiveui.com/en-US/light/components/color-picker"
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
			<CardCodeExample title="Basic" class="max-w-lg">
				<n-color-picker
					:swatches="['#FFFFFF', '#18A058', '#2080F0', '#F0A020', 'rgba(208, 48, 80, 1)']"
					:actions="['clear']"
				/>
				<template #code="{ html }">
					{{ html(`
					<n-color-picker
						:swatches="['#FFFFFF', '#18A058', '#2080F0', '#F0A020', 'rgba(208, 48, 80, 1)']"
						:actions="['clear']"
					/>
					`) }}
				</template>
			</CardCodeExample>
		</div>
	</div>
</template>

<script lang="ts" setup>
import { NIcon, NColorPicker } from "naive-ui"
import ExternalIcon from "@vicons/tabler/ExternalLink"
</script>
