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
const LicenseIcon = "carbon:license"
const LogoutIcon = "ion:log-out-outline"
const LogsIcon = "carbon:cloud-logging"
const ContactIcon = "ic:outline-alternate-email"
const UsersIcon = "carbon:group-security"

const router = useRouter()
const authStore = useAuthStore()

const userPic = authStore.userPic

const options = ref([
	{
		label: "Profile",
		key: "route-Profile",
		icon: renderIcon(UserIcon)
	},
	{
		label: "License",
		key: "route-License",
		icon: renderIcon(LicenseIcon)
	},
	{
		label: "Users",
		key: "route-Users",
		icon: renderIcon(UsersIcon)
	},
	{
		label: "Logs",
		key: "route-Logs",
		icon: renderIcon(LogsIcon)
	},
	{
		label: () =>
			h(
				"a",
				{
					href: "https://www.socfortress.co/contact-us",
					target: "_blank",
					rel: "noopenner noreferrer"
				},
				"Contact SOCFortress"
			),
		key: "contact-socfortress",
		icon: renderIcon(ContactIcon)
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
