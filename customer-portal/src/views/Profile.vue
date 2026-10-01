<template>
	<div class="page">
		<n-card class="header flex flex-col" content-class="p-0!">
			<div class="user-info flex flex-wrap">
				<div class="propic">
					<n-avatar :size="100" :src="userPic" round :img-props="{ alt: 'avatar' }" />
				</div>
				<div class="info flex grow flex-col justify-center">
					<div class="name">
						<h1>{{ userName }}</h1>
					</div>
					<div class="details flex flex-wrap">
						<div class="item">
							<n-tooltip placement="top">
								<template #trigger>
									<div class="tooltip-wrap">
										<Icon :name="RoleIcon" />
										<span>{{ userRole }}</span>
									</div>
								</template>
								<span>Role</span>
							</n-tooltip>
						</div>
						<div class="item">
							<n-tooltip placement="top">
								<template #trigger>
									<div class="tooltip-wrap">
										<Icon :name="CustomerCodeIcon" />
										<span>{{ userCustomerCode }}</span>
									</div>
								</template>
								<span>Customer Code</span>
							</n-tooltip>
						</div>
					</div>
				</div>
			</div>
			<div class="section-selector">
				<n-tabs v-model:value="tabActive">
					<n-tab name="settings">Settings</n-tab>
					<n-tab name="security">Security</n-tab>
				</n-tabs>
			</div>
		</n-card>
		<div class="main">
			<n-tabs v-model:value="tabActive" tab-class="hidden!" animated>
				<n-tab-pane name="settings">
					<ProfileSettings />
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
import { NAvatar, NCard, NTab, NTabPane, NTabs, NTooltip } from "naive-ui"
import { ref } from "vue"
import ChangePasswordCard from "@/components/auth/ChangePasswordCard.vue"
import TotpToggle from "@/components/auth/TotpToggle.vue"
import Icon from "@/components/common/Icon.vue"
import ProfileSettings from "@/components/profile/ProfileSettings.vue"
import { useAuthStore } from "@/stores/auth"

const RoleIcon = "carbon:user"
const CustomerCodeIcon = "carbon:hashtag"

const tabActive = ref("settings")
const authStore = useAuthStore()

const userRole = authStore.userRoleName
const userName = authStore.userName
const userCustomerCode = authStore.userCustomerCode
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
					margin-bottom: 12px;

					@media (max-width: 450px) {
						h1 {
							font-size: 28px;
						}
					}
				}

				.details {
					gap: 24px;

					.item {
						.tooltip-wrap {
							display: flex;
							align-items: center;
							gap: 8px;
							line-height: 1;
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
