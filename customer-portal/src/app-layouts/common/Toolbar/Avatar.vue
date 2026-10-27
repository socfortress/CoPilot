<template>
	<n-dropdown v-model:show="open" :options placement="bottom-end" trigger="click" @select="handleSelect">
		<!-- Who is signed in and as what, without opening the menu (#1296): avatar, username, role. -->
		<button
			type="button"
			class="border-default flex h-8 max-w-52 cursor-pointer items-center gap-2 rounded-full border bg-transparent p-0.5 sm:pr-3"
			:title="`${authStore.userName ?? ''} · ${roleText}`"
			data-testid="toolbar-avatar"
		>
			<n-avatar round :size="26" :src="userPic" :img-props="{ alt: '' }" class="shrink-0" />
			<span class="hidden min-w-0 flex-col items-start gap-0 leading-none sm:flex">
				<span class="text-default max-w-full truncate text-xs font-semibold" data-testid="toolbar-avatar-name">
					{{ authStore.userName }}
				</span>
				<span class="text-secondary text-xxs flex items-center gap-1.5" data-testid="toolbar-avatar-role">
					<span
						class="size-1.5 shrink-0 rounded-full"
						:style="{
							background: authStore.isCustomerAdmin ? 'var(--info-color)' : 'var(--fg-tertiary-color)'
						}"
					></span>
					{{ roleText }}
				</span>
			</span>
		</button>
	</n-dropdown>
</template>

<script lang="ts" setup>
import type { DropdownOption } from "naive-ui"
import { NAvatar, NDropdown, NTag, useMessage } from "naive-ui"
import { computed, h, ref, watch } from "vue"
import { useI18n } from "vue-i18n"
import { RouterLink, useRouter } from "vue-router"
import { useAuditAvailability } from "@/composables/common/useAuditAvailability"
import { isLocaleCode, LOCALE_NAMES } from "@/lang/config"
import { useAuthStore } from "@/stores/auth"
import { useLocalesStore } from "@/stores/i18n"
import { renderIcon } from "@/utils"

const LogoutIcon = "carbon:logout"
const UsersIcon = "carbon:user-multiple"
const AuditIcon = "carbon:catalog"
const LanguageIcon = "carbon:language"
const CheckIcon = "carbon:checkmark"

const router = useRouter()
const authStore = useAuthStore()
const localesStore = useLocalesStore()
const message = useMessage()
const { t } = useI18n()

const userPic = authStore.userPic
// A user who may only read every one of their customers' data is a read-only user (#1312).
const roleText = computed(() =>
	authStore.isCustomerAdmin
		? t("profile.roles.customerAdmin")
		: authStore.accessibleCustomers.length && !authStore.writableCustomers.length
			? t("profile.roles.readOnlyUser")
			: t("profile.roles.portalUser")
)

const open = ref(false)

// Who is signed in: the whole username (wrapped, never truncated) and the role. The card is
// the way to the Profile, so the menu has no separate Profile item.
function renderSignedInUser() {
	return h(
		RouterLink,
		{
			to: { name: "Profile" },
			class: "border-default bg-secondary hover:border-primary focus-visible:border-primary mx-2 mt-2 mb-1 flex max-w-80 min-w-56 items-center gap-3 rounded-lg border px-3 py-2.5 no-underline transition-colors outline-none",
			title: t("navigation.toolbar.yourProfile"),
			"data-testid": "toolbar-user",
			onClick: () => {
				open.value = false
			}
		},
		() => [
			h("span", { class: "flex shrink-0" }, [
				h(NAvatar, { round: true, size: 40, src: userPic, imgProps: { alt: "" } })
			]),
			h("div", { class: "flex min-w-0 flex-col gap-1" }, [
				h(
					"span",
					{ class: "text-default text-sm leading-snug font-semibold break-all" },
					authStore.userName ?? ""
				),
				h(
					NTag,
					{
						type: authStore.isCustomerAdmin ? "info" : "default",
						size: "tiny",
						bordered: false,
						class: "self-start font-mono text-[8px]! tracking-wider uppercase",
						"data-testid": "toolbar-role"
					},
					() => roleText.value
				)
			])
		]
	)
}

// "Audit log" for a customer admin whose SOC turned it on for one of their customers (#1298).
const { available: auditAvailable, check: checkAudit } = useAuditAvailability()
watch(
	() => authStore.isCustomerAdmin,
	isAdmin => {
		if (isAdmin) checkAudit()
	},
	{ immediate: true }
)

// The portal's language (#1310): only when the user's customers offer more than English.
const languageOption = computed<DropdownOption[]>(() => {
	if (!localesStore.canChoose) return []
	const children: DropdownOption[] = localesStore.available.map(code => ({
		label: LOCALE_NAMES[code],
		key: `locale-${code}`,
		icon: code === localesStore.locale ? renderIcon(CheckIcon) : undefined
	}))
	return [
		{
			label: t("common.language.label"),
			key: "language",
			icon: renderIcon(LanguageIcon),
			children
		}
	]
})

// "Users" only for a customer admin (#1296): the profile says so, read live.
const options = computed<DropdownOption[]>(() => [
	{ key: "signed-in-user", type: "render", render: renderSignedInUser },
	...(authStore.isCustomerAdmin ? [{ label: t("navigation.routes.users"), key: "route-Users", icon: renderIcon(UsersIcon) }] : []),
	...(authStore.isCustomerAdmin && auditAvailable.value
		? [{ label: t("navigation.routes.auditLog"), key: "route-AuditLog", icon: renderIcon(AuditIcon) }]
		: []),
	...languageOption.value,
	{
		label: t("navigation.toolbar.logout"),
		key: "route-Logout",
		icon: renderIcon(LogoutIcon)
	}
])

async function chooseLanguage(code: string) {
	if (!isLocaleCode(code) || code === localesStore.locale) return
	try {
		await localesStore.choose(code)
		message.success(t("common.language.saved"))
	} catch {
		message.error(t("common.language.failed"))
	}
}

function handleSelect(key: string) {
	if (key.startsWith("locale-")) {
		chooseLanguage(key.slice("locale-".length))
		return
	}
	if (key.indexOf("route-") === 0) {
		const path = key.split("route-")[1]
		router.push({ name: path })
	}
}
</script>
