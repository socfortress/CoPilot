<template>
	<n-dropdown :options placement="bottom-end" trigger="click" @select="handleSelect">
		<span
			class="relative inline-flex cursor-pointer"
			:title="signedInRole ? roleLabel(signedInRole) : undefined"
			data-testid="toolbar-avatar"
		>
			<n-avatar round :size="32" :src="userPic" :img-props="{ alt: 'avatar' }" />
			<!-- The role at a glance, in its tag colour; the menu names it in full. -->
			<span
				v-if="signedInRole"
				class="bg-default absolute -right-1 -bottom-1 flex size-4 items-center justify-center rounded-full border"
				:class="ROLE_TONE[roleTagType(signedInRole) ?? 'default']"
				role="img"
				:aria-label="roleLabel(signedInRole)"
				data-testid="toolbar-avatar-role"
			>
				<Icon :name="roleIcon(signedInRole)" :size="10" />
			</span>
		</span>
	</n-dropdown>
</template>

<script lang="ts" setup>
import { NAvatar, NDropdown, NTag } from "naive-ui"
import { computed, h, ref } from "vue"
import { useRouter } from "vue-router"
import Icon from "@/components/common/Icon.vue"
import { roleIcon, roleLabel, roleNameOf, roleTagType } from "@/components/users/roles"
import { useAuthStore } from "@/stores/auth"
import { renderIcon } from "@/utils"

const UserIcon = "ion:person-outline"
const LogoutIcon = "ion:log-out-outline"
const ContactIcon = "ic:outline-alternate-email"
const DocsIcon = "carbon:document"

const router = useRouter()
const authStore = useAuthStore()

const userPic = authStore.userPic
const signedInRole = computed(() => roleNameOf(authStore.userRole))

// Literal classes per tag type, so Tailwind sees them.
const ROLE_TONE: Record<string, string> = {
	error: "text-error border-error",
	primary: "text-primary border-primary",
	warning: "text-warning border-warning",
	info: "text-info border-info",
	success: "text-success border-success",
	default: "text-secondary border-default"
}

// Who is signed in: avatar, the whole username (wrapped, never truncated) and the role.
function renderSignedInUser() {
	const roleName = roleNameOf(authStore.userRole)
	return h(
		"div",
		{
			class: "border-default bg-secondary mx-2 mt-2 mb-1 flex max-w-80 min-w-64 items-center gap-3 rounded-lg border px-3 py-2.5",
			"data-testid": "avatar-user"
		},
		[
			h("div", { class: "relative shrink-0" }, [
				h(NAvatar, {
					round: true,
					size: 40,
					src: userPic,
					imgProps: { alt: "" }
				})
			]),
			h("div", { class: "flex min-w-0 flex-col gap-1 -mt-1.5" }, [
				h(
					"span",
					{
						class: "text-default text-sm leading-snug font-semibold break-all",
						"data-testid": "avatar-username"
					},
					authStore.userName
				),
				roleName
					? h(
							NTag,
							{
								type: roleTagType(roleName),
								size: "tiny",
								bordered: false,
								class: "self-start font-mono text-[8px]! tracking-wider uppercase",
								"data-testid": "avatar-role"
							},
							() => roleLabel(roleName)
						)
					: null
			])
		]
	)
}

const options = ref([
	{
		type: "render",
		key: "signed-in-user",
		render: renderSignedInUser
	},
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
