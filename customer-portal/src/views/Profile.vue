<template>
	<div class="page">
		<n-card class="header flex flex-col" content-class="p-0!">
			<div class="user-info flex flex-wrap">
				<div class="propic">
					<!-- A customer admin's avatar is ringed in the role's colour (#1296). -->
					<n-avatar
						:size="100"
						:src="userPic"
						round
						:img-props="{ alt: $t('profile.header.avatarAlt') }"
						:style="
							administered.length
								? { boxShadow: '0 0 0 3px var(--bg-default-color), 0 0 0 5px var(--info-color)' }
								: undefined
						"
						data-testid="profile-avatar"
					/>
				</div>
				<div class="info flex grow flex-col justify-center gap-3">
					<div class="name flex flex-wrap items-center gap-x-3 gap-y-1">
						<h1>{{ userName }}</h1>
						<n-tag
							v-if="administered.length"
							type="info"
							:bordered="false"
							data-testid="profile-customer-admin"
						>
							<template #icon><Icon name="carbon:user-multiple" :size="14" /></template>
							{{ $t("profile.roles.customerAdmin") }}
						</n-tag>
					</div>
					<!-- What the account is for, in one line: the SOC appointed a customer admin (#1296). -->
					<p class="text-secondary m-0 text-sm" data-testid="profile-role-description">
						<i18n-t v-if="administered.length" keypath="profile.header.managesUsersOf" scope="global">
							<template #customers>
								<bdi>{{ administered.map(customer => customer.customer_name).join(", ") }}</bdi>
							</template>
						</i18n-t>
						<template v-else>{{ $t("profile.roles.portalUser") }}</template>
					</p>
					<div class="flex flex-wrap items-center gap-2" data-testid="profile-customers">
						<span
							v-for="customer in customers"
							:key="customer.customer_code"
							class="border-default flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-sm"
							data-testid="profile-customer"
						>
							<CustomerName :code="customer.customer_code" />
							<span
								v-if="customer.is_customer_admin"
								class="text-info mt-0.5 font-mono text-[10px] leading-none font-semibold tracking-wider uppercase"
								data-testid="profile-customer-admin-of"
							>
								{{ $t("profile.header.adminBadge") }}
							</span>
						</span>
						<span v-if="!customers.length" class="text-secondary text-sm">
							{{ $t("profile.header.noCustomer") }}
						</span>
					</div>
				</div>
			</div>
			<div class="section-selector">
				<n-tabs v-model:value="tabActive">
					<n-tab name="settings">{{ $t("profile.tabs.settings") }}</n-tab>
					<n-tab v-if="notificationsOn" name="notifications" data-testid="profile-tab-notifications">
						{{ $t("profile.tabs.notifications") }}
					</n-tab>
					<n-tab name="security">{{ $t("profile.tabs.security") }}</n-tab>
				</n-tabs>
			</div>
		</n-card>
		<div class="main">
			<n-tabs v-model:value="tabActive" tab-class="hidden!" animated>
				<n-tab-pane name="settings">
					<ProfileSettings />
				</n-tab-pane>
				<n-tab-pane v-if="notificationsOn" name="notifications" display-directive="if">
					<NotificationPreferences />
				</n-tab-pane>
				<n-tab-pane name="security">
					<div class="flex flex-col gap-4">
						<ChangePasswordCard />
						<TotpToggle />
					</div>
				</n-tab-pane>
			</n-tabs>
		</div>
	</div>
</template>

<script lang="ts" setup>
import { NAvatar, NCard, NTab, NTabPane, NTabs, NTag } from "naive-ui"
import { computed, onBeforeMount, ref, watch } from "vue"
import { useRoute } from "vue-router"
import ChangePasswordCard from "@/components/auth/ChangePasswordCard.vue"
import TotpToggle from "@/components/auth/TotpToggle.vue"
import CustomerName from "@/components/common/CustomerName.vue"
import Icon from "@/components/common/Icon.vue"
import NotificationPreferences from "@/components/profile/NotificationPreferences.vue"
import ProfileSettings from "@/components/profile/ProfileSettings.vue"
import { useServerNotifications } from "@/composables/common/useServerNotifications"
import { useAuthStore } from "@/stores/auth"

// `?tab=notifications` opens it directly: the link in every notification email points here.
const tabActive = ref(useRoute().query.tab === "notifications" ? "notifications" : "settings")
// Only while the user's customer has portal notifications on (#1282).
const server = useServerNotifications()
const notificationsOn = server.available
// A link to the tab while notifications are off (or once they are switched off) shows Settings, never an empty page.
function leaveHiddenTab() {
	if (!notificationsOn.value && tabActive.value === "notifications") tabActive.value = "settings"
}
watch(notificationsOn, leaveHiddenTab)
onBeforeMount(async () => {
	await server.loadAvailability()
	leaveHiddenTab()
})
const authStore = useAuthStore()

const userName = authStore.userName
const customers = computed(() => authStore.accessibleCustomers)
const administered = computed(() => customers.value.filter(customer => customer.is_customer_admin))
const userPic = authStore.userPic
</script>

<style lang="scss" scoped>
.page {
	.header {
		.user-info {
			gap: 30px;
			padding: 30px;
			padding-bottom: 20px;
			border-block-end: 1px solid var(--border-color);

			.propic {
				height: 100px;
			}
			.info {
				.name {
					@media (max-width: 450px) {
						h1 {
							font-size: 28px;
						}
					}
				}
			}
		}
		.section-selector {
			padding: 0px 30px;
			padding-top: 15px;

			:deep() {
				.n-tabs .n-tabs-tab {
					padding-bottom: 20px;
				}
			}
		}
	}

	.main {
		margin-top: 18px;
	}
}
</style>
