<template>
	<div class="bg-body rounded-lg py-0.5" :class="{ collapsed }">
		<n-menu :options="menuOptions" :collapsed :collapsed-width :indent="18" />
	</div>
</template>

<script lang="ts" setup>
import { NMenu } from "naive-ui"
import { computed, h, ref } from "vue"
import { useThemeStore } from "@/stores/theme"
import { renderIcon } from "@/utils"

const { collapsed = false } = defineProps<{
	collapsed?: boolean
}>()

const BuyIcon = "carbon:shopping-cart"
const DocsIcon = "ion:book-outline"
const menuOptions = ref([
	{
		label: () =>
			h(
				"a",
				{
					href: "https://pinx-docs.vercel.app/",
					target: "_blank",
					rel: "noopenner noreferrer"
				},
				"Documentation"
			),
		key: "documentation",
		icon: renderIcon(DocsIcon)
	},
	{
		label: () =>
			h(
				"a",
				{
					href: "https://themeforest.net/item/pinx-vuejs-admin-template/47799543",
					target: "_blank",
					rel: "noopenner noreferrer"
				},
				"Buy now"
			),
		key: "buy-now",
		icon: renderIcon(BuyIcon)
	}
])

const themeStore = useThemeStore()
const collapsedWidth = computed<number>(() => themeStore.sidebar.closeWidth - 16)
</script>
