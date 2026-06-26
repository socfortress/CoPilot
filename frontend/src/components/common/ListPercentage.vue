<template>
	<div class="flex flex-col gap-2">
		<n-empty v-if="!list.length" description="No items found" class="h-48 justify-center" />

		<div class="text-secondary flex items-center justify-between gap-4 font-mono text-sm">
			<div class="border-default basis-2/3 truncate border-b pb-1">
				{{ labelKey }}
			</div>
			<div class="border-default grow border-b pb-1">
				{{ percentageKey }}
			</div>
		</div>
		<div
			v-for="item of list"
			:key="item?.[labelKey as keyof typeof item] ?? ''"
			class="flex items-center justify-between gap-4"
		>
			<div class="basis-2/3 truncate font-mono">
				{{ item?.[labelKey as keyof typeof item] ?? "" }}
			</div>
			<div class="grow">
				<n-progress
					type="line"
					:percentage="parseInt(String(item?.[percentageKey as keyof typeof item] ?? 0), 10)"
					indicator-placement="inside"
					:indicator-text-color="style['bg-default-color']"
					:color="style['fg-default-color']"
					:rail-color="style['border-color']"
					class="font-mono font-bold"
				/>
			</div>
		</div>
	</div>
</template>

<script setup lang="ts">
import type { SafeAny } from "@/types/common"
import { NEmpty, NProgress } from "naive-ui"
import { computed } from "vue"
import { useThemeStore } from "@/stores/theme"

const { list, labelKey, percentageKey } = defineProps<{
	list: SafeAny[]
	labelKey: string
	percentageKey: string
}>()

const themeStore = useThemeStore()

const style = computed(() => themeStore.style)
</script>
