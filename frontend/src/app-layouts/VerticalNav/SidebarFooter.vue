<template>
	<div class="sidebar-footer bg-body rounded-lg py-0.5" :class="{ collapsed }">
		<n-menu :options="menuOptions" :collapsed :collapsed-width :indent="18" />
	</div>
</template>

<script lang="ts" setup>
import { NMenu } from "naive-ui"
import { computed, h, ref } from "vue"
import { RouterLink } from "vue-router"
import { useThemeStore } from "@/stores/theme"
import { renderIcon } from "@/utils"

const { collapsed = false } = defineProps<{
	collapsed?: boolean
}>()

const ContactIcon = "ic:outline-alternate-email"
const DocsIcon = "carbon:document"
const LogoutIcon = "ion:log-out-outline"

const menuOptions = ref([
	{
		label: () =>
			h(
				"a",
				{
					href: "https://docs.socfortress.co/",
					target: "_blank",
					rel: "noopener noreferrer"
				},
				{ default: () => "Documentation" }
			),
		key: "documentation",
		icon: renderIcon(DocsIcon)
	},
	{
		label: () =>
			h(
				"a",
				{
					href: "https://www.socfortress.co/contact-us",
					target: "_blank",
					rel: "noopener noreferrer"
				},
				{ default: () => "Contact SOCFortress" }
			),
		key: "contact-socfortress",
		icon: renderIcon(ContactIcon)
	},
	{
		label: () =>
			h(
				RouterLink,
				{
					to: {
						name: "Logout"
					}
				},
				{ default: () => "Logout" }
			),
		key: "Logout",
		icon: renderIcon(LogoutIcon)
	}
])

const themeStore = useThemeStore()

const collapsedWidth = computed<number>(() => themeStore.sidebar.closeWidth - 16)
</script>
