<template>
	<n-dropdown :options placement="bottom-end" @select="handleSelect">
		<n-avatar round :size="32" :src="userPic" :img-props="{ alt: 'avatar' }" />
	</n-dropdown>
</template>

<script lang="ts" setup>
import { NAvatar, NDropdown } from "naive-ui"
import { h, ref } from "vue"
import { useRouter } from "vue-router"
import { useAuthStore } from "@/stores/auth"
import { renderIcon } from "@/utils"

const UserIcon = "ion:person-outline"
const LogoutIcon = "ion:log-out-outline"
const ContactIcon = "ic:outline-alternate-email"
const DocsIcon = "carbon:document"

const router = useRouter()
const authStore = useAuthStore()

const userPic = authStore.userPic

const options = ref([
	{
		label: "Profile",
		key: "route-Profile",
		icon: renderIcon(UserIcon)
	},
	// Settings pages (Users, SSO, Scheduler, Integrations, Audit, …) live in the
	// sidebar's Platform section since #1152; this menu is about the signed-in user.
	{
		type: "divider",
		key: "divider-1"
	},
	{
		label: () =>
			h(
				"a",
				{
					href: "https://docs.socfortress.co/",
					target: "_blank",
					rel: "noopener noreferrer"
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
					href: "https://www.socfortress.co/contact-us",
					target: "_blank",
					rel: "noopener noreferrer"
				},
				"Contact SOCFortress"
			),
		key: "contact-socfortress",
		icon: renderIcon(ContactIcon)
	},
	{
		type: "divider",
		key: "divider-2"
	},
	{
		label: "Logout",
		key: "route-Logout",
		icon: renderIcon(LogoutIcon)
	}
])
function handleSelect(key: string) {
	if (key.indexOf("route-") === 0) {
		const path = key.split("route-")[1]
		router.push({ name: path })
	}
}
</script>
