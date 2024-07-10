<template>
	<n-dropdown :options="options" placement="bottom-end" @select="handleSelect">
		<n-avatar round :size="32" :src="userPic" />
	</n-dropdown>
</template>

<script lang="ts" setup>
import { NAvatar, NDropdown } from "naive-ui"
import { renderIcon } from "@/utils"
import { useRouter } from "vue-router"
import { ref, h } from "vue"
import { useAuthStore } from "@/stores/auth"

const UserIcon = "ion:person-outline"
const LicenseIcon = "carbon:license"
const LogoutIcon = "ion:log-out-outline"
const LogsIcon = "carbon:cloud-logging"
const ContactIcon = "ic:outline-alternate-email"

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
		label: "Logs",
		key: "route-Logs",
		icon: renderIcon(LogsIcon)
	},
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
