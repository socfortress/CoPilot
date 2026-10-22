<template>
	<n-dropdown :options placement="bottom-end" trigger="click" @select="handleSelect">
		<span
			class="relative inline-flex cursor-pointer"
			:title="authStore.isCustomerAdmin ? 'Customer admin' : undefined"
			data-testid="toolbar-avatar"
		>
			<n-avatar round :size="32" :src="userPic" :img-props="{ alt: 'avatar' }" />
			<!-- A customer admin (#1296) is marked on the avatar itself, not only in the menu. -->
			<span
				v-if="authStore.isCustomerAdmin"
				class="bg-default text-info absolute -right-1 -bottom-1 flex size-4 items-center justify-center rounded-full"
				role="img"
				aria-label="Customer admin"
				data-testid="toolbar-avatar-admin"
			>
				<Icon name="carbon:user-admin" :size="11" />
			</span>
		</span>
	</n-dropdown>
</template>

<script lang="ts" setup>
import type { DropdownOption } from "naive-ui"
import { NAvatar, NDropdown, NTag } from "naive-ui"
import { computed, h } from "vue"
import { useRouter } from "vue-router"
import Icon from "@/components/common/Icon.vue"
import { useAuthStore } from "@/stores/auth"
import { renderIcon } from "@/utils"

const UserIcon = "carbon:user"
const LogoutIcon = "carbon:logout"
const UsersIcon = "carbon:user-multiple"

const router = useRouter()
const authStore = useAuthStore()

const userPic = authStore.userPic

// "Users" only for a customer admin (#1296), and the menu says what they are: the profile says so, read live.
const options = computed<DropdownOption[]>(() => [
	...(authStore.isCustomerAdmin
		? [
				{
					key: "role",
					type: "render",
					render: () =>
						h("div", { class: "px-3 pt-2 pb-1", "data-testid": "toolbar-role" }, [
							h(NTag, { type: "info", size: "small", bordered: false }, () => "Customer admin")
						])
				},
				{ key: "role-divider", type: "divider" }
			]
		: []),
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
