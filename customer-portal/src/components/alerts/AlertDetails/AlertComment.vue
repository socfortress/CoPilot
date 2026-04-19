<template>
	<CardEntity size="small" embedded>
		<template #header-main>{{ comment.user_name }}</template>
		<template #header-extra>{{ formatDate(comment.created_at, dFormats.datetime) }}</template>
		<template #default>
			<n-input
				v-if="editMode"
				v-model:value="newComment"
				type="textarea"
				:autosize="{ minRows: 3, maxRows: 10 }"
			/>
			<div v-else v-html="commentHtml"></div>
		</template>
		<template #footer-extra>
			<div v-if="editMode" class="flex items-center gap-2">
				<n-button
					size="tiny"
					type="primary"
					secondary
					:focusable="false"
					:disabled="!newComment?.trim()"
					:loading="updating"
					@click="updateComment"
				>
					<template #icon>
						<Icon name="carbon:save" />
					</template>
					Save
				</n-button>
				<n-button size="tiny" :focusable="false" :disabled="updating" @click="setEditMode(false)">
					<template #icon>
						<Icon name="carbon:delete" />
					</template>
					Cancel
				</n-button>
			</div>
			<div v-else class="flex items-center gap-2">
				<n-button size="tiny" :focusable="false" :disabled="deleting" @click="setEditMode(true)">
					<template #icon>
						<Icon name="carbon:edit" />
					</template>
					Edit
				</n-button>

				<n-popconfirm to="body" @positive-click="deleteComment">
					<template #trigger>
						<n-button size="tiny" :focusable="false" :loading="deleting">
							<template #icon>
								<Icon name="carbon:trash-can" />
							</template>
							Delete
						</n-button>
					</template>
					Are you sure you want to delete this comment?
				</n-popconfirm>
			</div>
		</template>
	</CardEntity>
</template>

<script setup lang="ts">
import type { CommentItem } from "@/types/comments"
import type { ApiError } from "@/types/common"
import { NButton, NInput, NPopconfirm, useMessage } from "naive-ui"
import { computed, ref } from "vue"
import Api from "@/api"
import CardEntity from "@/components/common/cards/CardEntity.vue"
import Icon from "@/components/common/Icon.vue"
import { useAuthStore } from "@/stores/auth"
import { useSettingsStore } from "@/stores/settings"
import { getApiErrorMessage } from "@/utils"
import { formatDate } from "@/utils/format"

const { comment, alertId } = defineProps<{
	comment: CommentItem
	alertId: number
}>()

const emit = defineEmits<{
	(e: "updated", comment: CommentItem): void
	(e: "deleted", commentId: number): void
}>()

const message = useMessage()
const authStore = useAuthStore()
const dFormats = useSettingsStore().dateFormat
const editMode = ref(false)
const newComment = ref<string | null>(null)
const updating = ref(false)
const deleting = ref(false)
const NEWLINE_REGEX = /\n/g

const commentHtml = computed(() => {
	return comment.comment.replace(NEWLINE_REGEX, "<br>")
})

function setEditMode(mode: boolean) {
	editMode.value = mode

	if (mode) {
		newComment.value = comment.comment
	}
}

async function updateComment() {
	if (!alert || !newComment.value?.trim()) return

	updating.value = true

	try {
		const response = await Api.alerts.updateComment({
			alertId,
			commentId: comment.id,
			comment: newComment.value.trim(),
			userName: authStore.userName || ""
		})

		emit("updated", response.data.comment)
		newComment.value = ""
		message.success(response.data?.message || "Comment updated successfully")
		setEditMode(false)
	} catch (err) {
		message.error(getApiErrorMessage(err as ApiError))
	} finally {
		updating.value = false
	}
}

async function deleteComment() {
	if (!comment) return

	deleting.value = true

	try {
		const response = await Api.alerts.deleteComment(comment.id)
		emit("deleted", comment.id)
		message.success(response.data?.message || "Comment deleted successfully")
	} catch (err) {
		message.error(getApiErrorMessage(err as ApiError))
	} finally {
		deleting.value = false
	}
}
</script>
