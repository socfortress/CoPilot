<template>
	<div class="page">
		<n-card class="header flex flex-col" content-class="p-0!">
			<div class="user-info flex flex-wrap">
				<div class="propic">
					<n-avatar
						:size="100"
						:src="userPic"
						round
						:img-props="{ alt: 'avatar' }"
						:style="roleName ? { boxShadow: `0 0 0 3px var(--bg-default-color), 0 0 0 5px ${roleColor(roleName)}` } : undefined"
						data-testid="profile-avatar"
					/>
					<ImageCropper
						v-if="propicEnabled"
						v-slot="{ openCropper }"
						shape="circle"
						placeholder="Select your profile picture"
						@crop="setCroppedImage"
					>
						<Icon :name="EditIcon" :size="16" class="edit" @click="openCropper()" />
					</ImageCropper>
				</div>
				<div class="info flex grow flex-col justify-center">
					<div class="name flex flex-wrap items-center gap-x-3 gap-y-1">
						<h1>{{ userName }}</h1>
						<n-tag v-if="roleName" :type="roleTagType(roleName)" :bordered="false" data-testid="profile-role">
							<template #icon><Icon :name="roleIcon(roleName)" :size="14" /></template>
							{{ roleLabel(roleName) }}
						</n-tag>
					</div>
					<p
						v-if="roleDescription(roleName)"
						class="text-secondary m-0 mb-3 text-sm"
						data-testid="profile-role-description"
					>
						{{ roleDescription(roleName) }}
					</p>
					<div class="details flex flex-wrap">
						<div v-if="scopeText" class="item" data-testid="profile-scope">
							<div class="tooltip-wrap">
								<Icon :name="CustomersIcon" />
								<n-button
									v-if="scope === 'assigned'"
									text
									class="text-secondary!"
									data-testid="profile-scope-link"
									@click="tabActive = 'customers'"
								>
									{{ scopeText }}
								</n-button>
								<span v-else>{{ scopeText }}</span>
							</div>
						</div>
						<div v-if="userEmail" class="item">
							<div class="tooltip-wrap">
								<Icon :name="EmailIcon" />
								<span>{{ userEmail }}</span>
							</div>
						</div>
					</div>
				</div>
				<div class="actions">
					<ImageCropper
						v-if="propicEnabled"
						v-slot="{ openCropper }"
						shape="circle"
						placeholder="Select your profile picture"
						@crop="setCroppedImage"
					>
						<n-button size="large" type="primary" @click="openCropper()">Edit profile image</n-button>
					</ImageCropper>
				</div>
			</div>
			<div class="section-selector">
				<n-tabs v-model:value="tabActive">
					<n-tab name="settings">Settings</n-tab>
					<n-tab name="security">Security</n-tab>
					<n-tab name="customers">Customers</n-tab>
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
						<PasskeyToggle />
					</div>
				</n-tab-pane>
				<n-tab-pane name="customers">
					<ProfileCustomers />
				</n-tab-pane>
			</n-tabs>
		</div>
	</div>
</template>

<script lang="ts" setup>
import type { ImageCropperResult } from "@/components/common/ImageCropper.vue"
import { NAvatar, NButton, NCard, NTab, NTabPane, NTabs, NTag } from "naive-ui"
import { computed, onBeforeMount, ref } from "vue"
import Api from "@/api"
import ChangePasswordCard from "@/components/auth/ChangePassword.vue"
import PasskeyToggle from "@/components/auth/PasskeyToggle.vue"
import TotpToggle from "@/components/auth/TotpToggle.vue"
import Icon from "@/components/common/Icon.vue"
import ImageCropper from "@/components/common/ImageCropper.vue"
import ProfileCustomers from "@/components/profile/ProfileCustomers.vue"
import ProfileSettings from "@/components/profile/ProfileSettings.vue"
import {
	needsCustomers,
	roleColor,
	roleDescription,
	roleIcon,
	roleLabel,
	roleNameOf,
	roleTagType,
	seesEveryCustomer
} from "@/components/users/roles"

import { useAuthStore } from "@/stores/auth"

const propicEnabled = false

const EditIcon = "uil:image-edit"
const EmailIcon = "carbon:email"
const CustomersIcon = "carbon:enterprise"

const tabActive = ref("settings")
const authStore = useAuthStore()

const roleName = roleNameOf(authStore.userRole)
const userName = authStore.userName

// Which customers the role reaches, in one line; the Customers tab lists them.
const scope = ref<"assigned" | "deployment" | "unassigned" | null>(null)
const assignedCount = ref(0)
const scopeText = computed(() => {
	if (scope.value === "deployment") return "All customers"
	if (scope.value === "unassigned") return "No customers assigned"
	if (scope.value === "assigned") {
		return `${assignedCount.value} ${assignedCount.value === 1 ? "customer" : "customers"} assigned`
	}
	return ""
})

onBeforeMount(async () => {
	if (!needsCustomers(roleName) && !seesEveryCustomer(roleName)) return
	try {
		const res = await Api.auth.getMyCustomerAccess()
		const codes = res.data.customer_codes ?? []
		scope.value = res.data.scope ?? (codes.includes("*") ? "deployment" : codes.length ? "assigned" : "unassigned")
		assignedCount.value = codes.filter(code => code !== "*").length
	} catch {
		// The line is a summary: without an answer it is simply left out.
	}
})
const userEmail = authStore.userEmail
const userPic = ref(authStore.userPic)

function setCroppedImage(result: ImageCropperResult) {
	const canvas = result.canvas as HTMLCanvasElement
	userPic.value = canvas.toDataURL()
}
</script>

<style lang="scss" scoped>
.page {
	.header {
		.user-info {
			gap: 30px;
			padding: 30px;
			padding-bottom: 20px;
			border-block-end: 1px solid var(--border-color);
			container-type: inline-size;

			.propic {
				position: relative;
				height: 100px;

				.edit {
					display: none;
					align-items: center;
					justify-content: center;
					background-color: var(--primary-color);
					color: var(--bg-default-color);
					position: absolute;
					width: 26px;
					height: 26px;
					border-radius: 50%;
					top: -1px;
					right: -1px;
					border: 1px solid var(--bg-default-color);
					cursor: pointer;
				}
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

			@container (max-width: 900px) {
				.propic {
					.edit {
						display: flex;
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
