<template>
	<div class="page">
		<n-card class="header flex flex-col" content-class="p-0!">
			<div class="user-info flex flex-wrap">
				<div class="propic">
					<n-avatar :size="100" :src="userPic" round :img-props="{ alt: 'avatar' }" />
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
						<div v-if="userEmail" class="item">
							<div class="tooltip-wrap">
								<Icon :name="EmailIcon" />
								<span>{{ userEmail }}</span>
							</div>
						</div>
					</div>
				</div>
				<div class="actions">
					<ChangePassword :user="{ username: userName, id: 0, email: '' }" size="small" />

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
				</n-tabs>
			</div>
		</n-card>
		<div class="main">
			<n-tabs v-model:value="tabActive" tab-class="!hidden" animated>
				<n-tab-pane name="settings">
					<ProfileSettings />
				</n-tab-pane>
			</n-tabs>
		</div>
	</div>
</template>

<script lang="ts" setup>
import type { ImageCropperResult } from "@/components/common/ImageCropper.vue"
import { NAvatar, NButton, NCard, NTab, NTabPane, NTabs, NTooltip } from "naive-ui"
import { ref } from "vue"
import Icon from "@/components/common/Icon.vue"
import ImageCropper from "@/components/common/ImageCropper.vue"
import ProfileSettings from "@/components/profile/ProfileSettings.vue"
import ChangePassword from "@/components/users/ChangePassword.vue"
import { useAuthStore } from "@/stores/auth"

const propicEnabled = false

const RoleIcon = "tabler:user"
const EditIcon = "uil:image-edit"
const EmailIcon = "carbon:email"

const tabActive = ref("settings")
const authStore = useAuthStore()

const userRole = authStore.userRoleName
const userName = authStore.userName
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
