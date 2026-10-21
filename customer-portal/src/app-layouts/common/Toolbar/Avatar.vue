<template>
	<n-dropdown :options placement="bottom-end" trigger="click" @select="handleSelect">
		<n-avatar round :size="32" :src="userPic" class="cursor-pointer" :img-props="{ alt: 'avatar' }" />
	</n-dropdown>
</template>

<script lang="ts" setup>
import type { DropdownOption } from "naive-ui"
import { NAvatar, NDropdown } from "naive-ui"
import { computed } from "vue"
import { useRouter } from "vue-router"
import { useAuthStore } from "@/stores/auth"
import { renderIcon } from "@/utils"

const UserIcon = "carbon:user"
const LogoutIcon = "carbon:logout"
const UsersIcon = "carbon:user-multiple"

const router = useRouter()
const authStore = useAuthStore()

const userPic = authStore.userPic

// "Users" only for a customer admin (#1296): the profile says so, read live.
const options = computed<DropdownOption[]>(() => [
	{
		label: "Profile",
		key: "route-Profile",
		icon: renderIcon(UserIcon)
	},
	...(authStore.isCustomerAdmin ? [{ label: "Users", key: "route-Users", icon: renderIcon(UsersIcon) }] : []),
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
