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
