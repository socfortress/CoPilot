<template>
	<n-card class="!bg-indigo-500 dark:!bg-teal-600">
		<template #header>
			<div class="flex items-center justify-between !text-white">
				<span>Alt Background</span>
				<n-icon class="ml-3 icon-ring">
					<ColorIcon />
				</n-icon>
			</div>
		</template>
		<div class="!text-white">
			Card with alternative background (light/dark). Color value from
			<strong>Tailwind</strong>
			class:
			<br />
			<br />
			<code class="w-full block p-4 text-center">class="!bg-indigo-500 dark:!bg-teal-600"</code>
		</div>
	</n-card>
</template>
<script setup lang="ts">
import { NCard, NIcon } from "naive-ui"
import ColorIcon from "@vicons/ionicons5/ColorFillOutline"
</script>

<style scoped lang="scss">
.icon-ring {
	background-color: rgba(var(--fg-color-rgb), 0.05);
	width: 30px;
	height: 30px;
	border-radius: 50%;
	display: flex;
	justify-content: center;
	align-items: center;
}
</style>
