<template>
	<n-dropdown :options placement="bottom-end" trigger="click" @select="handleSelect">
		<!-- Who is signed in and as what, without opening the menu (#1296): avatar, username, role. -->
		<button
			type="button"
			class="border-default flex max-w-52 cursor-pointer items-center gap-2 rounded-full border bg-transparent p-0.5 sm:pr-3"
			:title="`${authStore.userName ?? ''} · ${roleText}`"
			data-testid="toolbar-avatar"
		>
			<n-avatar round :size="28" :src="userPic" :img-props="{ alt: '' }" class="shrink-0" />
			<span class="hidden min-w-0 flex-col items-start gap-0.5 leading-tight sm:flex">
				<span class="text-default max-w-full truncate text-xs font-semibold" data-testid="toolbar-avatar-name">
					{{ authStore.userName }}
				</span>
				<span class="text-secondary flex items-center gap-1.5 text-[11px]" data-testid="toolbar-avatar-role">
					<span
						class="size-1.5 shrink-0 rounded-full"
						:style="{ background: authStore.isCustomerAdmin ? 'var(--info-color)' : 'var(--fg-tertiary-color)' }"
					></span>
					{{ roleText }}
				</span>
			</span>
		</button>
	</n-dropdown>
</template>

<script lang="ts" setup>
import type { DropdownOption } from "naive-ui"
import { NAvatar, NDropdown, NTag } from "naive-ui"
import { computed, h } from "vue"
import { useRouter } from "vue-router"
import { useAuthStore } from "@/stores/auth"
import { renderIcon } from "@/utils"

const UserIcon = "carbon:user"
const LogoutIcon = "carbon:logout"
const UsersIcon = "carbon:user-multiple"

const router = useRouter()
const authStore = useAuthStore()

const userPic = authStore.userPic
const roleText = computed(() => (authStore.isCustomerAdmin ? "Customer admin" : "Portal user"))

// Who is signed in: the whole username (wrapped, never truncated) and, for a customer admin, the role.
function renderSignedInUser() {
	return h(
		"div",
		{
			class: "border-default bg-secondary mx-2 mt-2 mb-1 flex max-w-80 min-w-56 items-center gap-3 rounded-lg border px-3 py-2.5",
			"data-testid": "toolbar-user"
		},
		[
			h("span", { class: "flex shrink-0" }, [h(NAvatar, { round: true, size: 40, src: userPic, imgProps: { alt: "" } })]),
			h("div", { class: "flex min-w-0 flex-col gap-1" }, [
				h("span", { class: "text-default text-sm leading-snug font-semibold break-all" }, authStore.userName ?? ""),
				authStore.isCustomerAdmin
					? h(
							NTag,
							{
								type: "info",
								size: "tiny",
								bordered: false,
								class: "self-start font-mono text-[8px]! tracking-wider uppercase",
								"data-testid": "toolbar-role"
							},
							() => "Customer admin"
						)
					: null
			])
		]
	)
}

// "Users" only for a customer admin (#1296): the profile says so, read live.
const options = computed<DropdownOption[]>(() => [
	{ key: "signed-in-user", type: "render", render: renderSignedInUser },
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
