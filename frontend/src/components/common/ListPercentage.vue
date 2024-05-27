<template>
	<div class="flex flex-col gap-2">
		<n-empty description="No items found" class="justify-center h-48" v-if="!list.length" />

		<div class="flex gap-4 justify-between items-center list-header font-mono text-secondary-color text-sm">
			<div class="basis-2/3 truncate borde">{{ labelKey }}</div>
			<div class="grow">{{ percentageKey }}</div>
		</div>
		<div class="flex gap-4 justify-between items-center" v-for="item of list" :key="item[labelKey]">
			<div class="basis-2/3 truncate font-mono">{{ item[labelKey] }}</div>
			<div class="grow">
				<n-progress
					type="line"
					:percentage="item[percentageKey]"
					:indicator-placement="'inside'"
					:indicator-text-color="style['--bg-color']"
					:color="style['--fg-color']"
					:rail-color="style['--divider-020-color']"
					class="font-mono font-bold"
				/>
			</div>
		</div>
	</div>
</template>

<script setup lang="ts">
import { useThemeStore } from "@/stores/theme"
import { NEmpty, NProgress } from "naive-ui"
import { computed } from "vue"

const { list, labelKey, percentageKey } = defineProps<{
	list: any[]
	labelKey: string
	percentageKey: string
}>()

const themeStore = useThemeStore()

const style = computed<{ [key: string]: any }>(() => themeStore.style)
</script>

<style scoped lang="scss">
.list-header {
	& > * {
		border-bottom: var(--border-small-100);
		@apply pb-1;
	}
}
</style>
