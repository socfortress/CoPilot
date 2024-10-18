<template>
	<div class="flex flex-col gap-2">
		<n-empty v-if="!list.length" description="No items found" class="h-48 justify-center" />

		<div class="list-header text-secondary flex items-center justify-between gap-4 font-mono text-sm">
			<div class="borde basis-2/3 truncate">
				{{ labelKey }}
			</div>
			<div class="grow">
				{{ percentageKey }}
			</div>
		</div>
		<div
			v-for="item of list"
			:key="item[labelKey as keyof typeof item]"
			class="flex items-center justify-between gap-4"
		>
			<div class="basis-2/3 truncate font-mono">
				{{ item[labelKey as keyof typeof item] }}
			</div>
			<div class="grow">
				<n-progress
					type="line"
					:percentage="parseInt(item[percentageKey as keyof typeof item], 10)"
					indicator-placement="inside"
					:indicator-text-color="style['bg-color']"
					:color="style['fg-color']"
					:rail-color="style['divider-020-color']"
					class="font-mono font-bold"
				/>
			</div>
		</div>
	</div>
</template>

<script setup lang="ts">
import type { SafeAny } from "@/types/common.d"
import { useThemeStore } from "@/stores/theme"
import { NEmpty, NProgress } from "naive-ui"
import { computed } from "vue"

const { list, labelKey, percentageKey } = defineProps<{
	list: SafeAny[]
	labelKey: string
	percentageKey: string
}>()

const themeStore = useThemeStore()

const style = computed(() => themeStore.style)
</script>

<style scoped lang="scss">
.list-header {
	& > * {
		border-bottom: var(--border-small-100);
		@apply pb-1;
	}
}
</style>
