<template>
	<div class="sidebar-footer" :class="{ collapsed }">
		<n-menu :options="menuOptions" :collapsed="collapsed" :collapsed-width="collapsedWidth" />
	</div>
</template>

<script lang="ts" setup>
import { useThemeStore } from "@/stores/theme"
import { renderIcon } from "@/utils"
import { NMenu } from "naive-ui"
import { computed, h, ref } from "vue"

const { collapsed = false } = defineProps<{
	collapsed?: boolean
}>()
const ContactIcon = "ic:outline-alternate-email"
const menuOptions = ref([
	{
		label: () =>
			h(
				"a",
				{
					href: "https://www.socfortress.co/contact_form.html",
					target: "_blank",
					rel: "noopenner noreferrer"
				},
				"Contact SOCFortress"
			),
		key: "contact-socfortress",
		icon: renderIcon(ContactIcon)
	}
])
const themeStore = useThemeStore()
const collapsedWidth = computed<number>(() => themeStore.sidebar.closeWidth - 16)
</script>

<style lang="scss" scoped>
.sidebar-footer {
	margin: 8px;
	background-color: var(--bg-body-color);
	border-radius: var(--border-radius);
	padding: 3px 0;
	transition: all 0.3s;

	:deep() {
		.n-menu {
			.n-menu-item-content.n-menu-item-content--selected::before {
				background-color: transparent !important;
			}
		}
	}
}
</style>
