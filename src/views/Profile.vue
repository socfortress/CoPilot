<template>
	<div class="page">
		<n-card class="header flex flex-col" content-style="padding:0">
			<div class="user-info flex flex-wrap">
				<div class="propic">
					<n-avatar :size="100" :src="userPic" round />
					<ImageCropper
						v-if="propicEnabled"
						v-slot="{ openCropper }"
						@crop="setCroppedImage"
						:placeholder="'Select your profile picture'"
					>
						<Icon :name="EditIcon" :size="16" class="edit" @click="openCropper()"></Icon>
					</ImageCropper>
				</div>
				<div class="info grow flex flex-col justify-center">
					<div class="name">
						<h1>{{ userName }}</h1>
					</div>
					<div class="details flex flex-wrap">
						<div class="item">
							<n-tooltip placement="top">
								<template #trigger>
									<div class="tooltip-wrap">
										<Icon :name="RoleIcon"></Icon>
										<span>{{ userRole }}</span>
									</div>
								</template>
								<span>Role</span>
							</n-tooltip>
						</div>
					</div>
				</div>
				<div class="actions">
					<ImageCropper
						v-if="propicEnabled"
						v-slot="{ openCropper }"
						@crop="setCroppedImage"
						:placeholder="'Select your profile picture'"
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
			<n-tabs :tab-style="{ display: 'none' }" v-model:value="tabActive" animated>
				<n-tab-pane name="settings">
					<ProfileSettings />
				</n-tab-pane>
			</n-tabs>
		</div>
	</div>
</template>

<script lang="ts" setup>
import { NAvatar, NButton, NTooltip, NTab, NTabs, NTabPane, NCard } from "naive-ui"
import { ref } from "vue"
import ImageCropper, { type ImageCropperResult } from "@/components/common/ImageCropper.vue"
import ProfileSettings from "@/components/profile/ProfileSettings.vue"
import Icon from "@/components/common/Icon.vue"
import { useAuthStore } from "@/stores/auth"

const propicEnabled = false

const RoleIcon = "tabler:user"
const EditIcon = "uil:image-edit"

const tabActive = ref("settings")

const userRole = useAuthStore().userRoleName
const userName = useAuthStore().userName
const userPic = ref(useAuthStore().userPic)

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
			border-block-end: var(--border-small-050);
			container-type: inline-size;

			.propic {
				position: relative;
				height: 100px;

				.edit {
					display: none;
					align-items: center;
					justify-content: center;
					background-color: var(--primary-color);
					color: var(--bg-color);
					position: absolute;
					width: 26px;
					height: 26px;
					border-radius: 50%;
					top: -1px;
					right: -1px;
					border: 1px solid var(--bg-color);
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

							span {
								line-height: 1;
								margin-left: 8px;
							}
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
				.actions {
					display: none;
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
