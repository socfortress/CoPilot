<template>
	<n-dropdown :options="options" placement="bottom-end" @select="handleSelect">
		<n-avatar round :size="32" src="/images/avatar-64.jpg" />
	</n-dropdown>
</template>

<script lang="ts" setup>
import { NAvatar, NDropdown } from "naive-ui"
import { renderIcon } from "@/utils"
import { useRouter } from "vue-router"
import { ref, h } from "vue"

const UserIcon = "ion:person-outline"
const LogoutIcon = "ion:log-out-outline"
const DocsIcon = "ion:book-outline"

defineOptions({
	name: "Avatar"
})

const router = useRouter()

const options = ref([
	{
		label: "Profile",
		key: "route-Profile",
		icon: renderIcon(UserIcon)
	},
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
