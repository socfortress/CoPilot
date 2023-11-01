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
				>
					<Icon :name="ExternalIcon" :size="16" />
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
import { NColorPicker } from "naive-ui"
import Icon from "@/components/common/Icon.vue"
const ExternalIcon = "tabler:external-link"
</script>
