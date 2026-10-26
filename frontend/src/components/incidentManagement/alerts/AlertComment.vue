<template>
	<div class="flex w-full gap-3">
		<div class="pt-0.5">
			<CommentAuthorAvatar :user-name="comment.user_name" :role="authorRole" />
		</div>
		<div class="flex grow flex-col gap-1 overflow-hidden">
			<div class="ml-0.5 flex items-center gap-3">
				<div class="font-semibold">
					{{ comment.user_name }}
				</div>
				<n-tag
					v-if="authorRole"
					:type="roleTagType(authorRole)"
					size="tiny"
					round
					:bordered="false"
					data-testid="comment-author-role"
				>
					{{ roleLabel(authorRole) }}
				</n-tag>
				<div class="text-secondary text-2xs font-mono">
					{{ formatDate(comment.created_at, dFormats.datetime) }}
				</div>
			</div>
			<div
				v-if="mode === 'view'"
				class="border-default rounded-lg border px-2.5 py-2 whitespace-pre-wrap"
				:class="embedded ? 'bg-secondary' : 'bg-default'"
			>
				{{ comment.comment }}
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
							<Icon :name="EditIcon" :size="12" />
						</template>
						<span>Edit</span>
					</n-button>
					<n-popconfirm to="body" @positive-click="deleteAlertComment()">
						<template #trigger>
							<n-button size="tiny" secondary type="error" :loading="canceling">
								<template #icon>
									<Icon :name="DeleteIcon" :size="12" />
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
							<Icon :name="ArrowLeftIcon" :size="12" />
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
							<Icon :name="SaveIcon" :size="13" />
						</template>
						<span>Save</span>
					</n-button>
				</template>
			</div>
		</div>
	</div>
</template>

<script setup lang="ts">
import type { ApiError } from "@/types/common"
import type { AlertComment } from "@/types/incidentManagement/alerts"
import { NButton, NInput, NPopconfirm, NTag, useMessage } from "naive-ui"
import { ref, toRefs } from "vue"
import Api from "@/api"
import Icon from "@/components/common/Icon.vue"
import { roleLabel, roleTagType } from "@/components/users/roles"
import { useSettingsStore } from "@/stores/settings"

import { getApiErrorMessage } from "@/utils"
import { formatDate } from "@/utils/format"
import CommentAuthorAvatar from "../common/CommentAuthorAvatar.vue"

type Mode = "view" | "edit"

// authorRole: the role name of the comment's author, when the list could read it (#1305).
const props = defineProps<{ comment: AlertComment; embedded?: boolean; authorRole?: string | null }>()

const emit = defineEmits<{
	(e: "deleted"): void
	(e: "updated", value: AlertComment): void
}>()

const { comment, embedded, authorRole } = toRefs(props)

const ArrowLeftIcon = "carbon:arrow-left"
const SaveIcon = "carbon:save"
const EditIcon = "uil:edit-alt"
const DeleteIcon = "ph:trash"
const mode = ref<Mode>("view")
const canceling = ref(false)
const saving = ref(false)
const dFormats = useSettingsStore().dateFormat
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
			message.error(getApiErrorMessage(err as ApiError) || "An error occurred. Please try again later.")
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
			message.error(getApiErrorMessage(err as ApiError) || "An error occurred. Please try again later.")
		})
		.finally(() => {
			canceling.value = false
		})
}
</script>
