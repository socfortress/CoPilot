<template>
	<div class="alert-comment-item flex gap-3" :class="{ embedded }">
		<div v-if="userPic" class="user-pic">
			<n-avatar round :size="32" :src="userPic" />
		</div>
		<div class="comment flex grow flex-col gap-1 overflow-hidden">
			<div class="user flex items-center gap-3">
				<div class="user-name">
					{{ comment.user_name }}
				</div>
				<div class="comment-time">
					{{ formatDate(comment.created_at, dFormats.datetime) }}
				</div>
			</div>
			<div v-if="mode === 'view'" class="comment-message">
				<Markdown :source="comment.comment" />
			</div>

			<n-input
				v-if="mode === 'edit'"
				v-model:value="commentModel"
				type="textarea"
				:disabled="saving"
				placeholder="Insert the updated comment"
				size="large"
				:autosize="{
					minRows: 3,
					maxRows: 18
				}"
			/>

			<div class="comment-actions flex justify-end gap-1">
				<template v-if="mode === 'view'">
					<n-button size="tiny" secondary :disabled="canceling" @click="editComment()">
						<template #icon>
							<Icon :name="EditIcon" :size="12"></Icon>
						</template>
						<span>Edit</span>
					</n-button>
					<n-popconfirm to="body" @positive-click="deleteAlertComment()">
						<template #trigger>
							<n-button size="tiny" secondary type="error" :loading="canceling">
								<template #icon>
									<Icon :name="DeleteIcon" :size="12"></Icon>
								</template>
								<span>Delete</span>
							</n-button>
						</template>
						Are you sure you want to delete the comment?
					</n-popconfirm>
				</template>
				<template v-if="mode === 'edit'">
					<n-button size="tiny" secondary :disabled="saving" @click="setMode('view')">
						<template #icon>
							<Icon :name="ArrowLeftIcon" :size="12"></Icon>
						</template>
						<span>Cancel</span>
					</n-button>

					<n-button
						size="tiny"
						secondary
						type="success"
						:loading="saving"
						:disabled="!commentModel"
						@click="updateAlertComment()"
					>
						<template #icon>
							<Icon :name="SaveIcon" :size="13"></Icon>
						</template>
						<span>Save</span>
					</n-button>
				</template>
			</div>
		</div>
	</div>
</template>

<script setup lang="ts">
import type { AlertComment } from "@/types/incidentManagement/alerts.d"
import { NAvatar, NButton, NInput, NPopconfirm, useMessage } from "naive-ui"
import { defineAsyncComponent, onBeforeMount, ref, toRefs } from "vue"
import Api from "@/api"
import Icon from "@/components/common/Icon.vue"
import { useSettingsStore } from "@/stores/settings"
import { formatDate, getAvatar, getNameInitials } from "@/utils"

type Mode = "view" | "edit"

const props = defineProps<{ comment: AlertComment; embedded?: boolean }>()

const emit = defineEmits<{
	(e: "deleted"): void
	(e: "updated", value: AlertComment): void
}>()

const Markdown = defineAsyncComponent(() => import("@/components/common/Markdown.vue"))

const { comment, embedded } = toRefs(props)

const ArrowLeftIcon = "carbon:arrow-left"
const SaveIcon = "carbon:save"
const EditIcon = "uil:edit-alt"
const DeleteIcon = "ph:trash"
const mode = ref<Mode>("view")
const canceling = ref(false)
const saving = ref(false)
const dFormats = useSettingsStore().dateFormat
const userPic = ref("")
const commentModel = ref(comment.value.comment)
const message = useMessage()

function setMode(newMode: Mode) {
	mode.value = newMode
}

function editComment() {
	setMode("edit")
	commentModel.value = comment.value.comment
}

function updateAlertComment() {
	saving.value = true

	Api.incidentManagement.alerts
		.updateAlertComment({
			alert_id: comment.value.alert_id,
			comment_id: comment.value.id,
			comment: commentModel.value,
			created_at: new Date(),
			user_name: comment.value.user_name
		})
		.then(res => {
			if (res.data.success) {
				message.success(res.data?.message || "Comment updated successfully")
				setMode("view")
				emit("updated", res.data.comment)
			} else {
				message.warning(res.data?.message || "An error occurred. Please try again later.")
			}
		})
		.catch(err => {
			message.error(err.response?.data?.message || "An error occurred. Please try again later.")
		})
		.finally(() => {
			saving.value = false
		})
}

function deleteAlertComment() {
	canceling.value = true

	Api.incidentManagement.alerts
		.deleteAlertComment(comment.value.id)
		.then(res => {
			if (res.data.success) {
				message.success(res.data?.message || "Comment deleted successfully")
				emit("deleted")
			} else {
				message.warning(res.data?.message || "An error occurred. Please try again later.")
			}
		})
		.catch(err => {
			message.error(err.response?.data?.message || "An error occurred. Please try again later.")
		})
		.finally(() => {
			canceling.value = false
		})
}

onBeforeMount(() => {
	const initials = getNameInitials(comment.value.user_name)
	userPic.value = getAvatar({ seed: initials, text: initials, size: 64 })
})
</script>

<style lang="scss" scoped>
.alert-comment-item {
	width: 100%;

	.user-pic {
		padding-top: 2px;
	}

	.comment {
		.user {
			margin-left: 2px;

			.user-name {
				font-weight: 600;
			}

			.comment-time {
				font-size: 11px;
				color: var(--fg-secondary-color);
				font-family: var(--font-family-mono);
			}
		}

		.comment-message {
			border-radius: var(--border-radius);
			background-color: var(--bg-default-color);
			border: 1px solid var(--border-color);
			padding: 6px 10px;
		}
	}

	&.embedded {
		.comment {
			.comment-message {
				background-color: var(--bg-secondary-color);
			}
		}
	}
}
</style>
