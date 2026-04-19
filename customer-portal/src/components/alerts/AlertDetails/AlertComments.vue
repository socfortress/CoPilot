<template>
	<div class="flex flex-col gap-2">
		<div v-if="alert.comments?.length" class="flex flex-col gap-2">
			<AlertComment
				v-for="comment in alert.comments"
				:key="comment.id"
				:comment
				:alert-id="alert.id"
				@updated="handleCommentUpdated"
				@deleted="handleCommentDeleted"
			/>
		</div>

		<n-empty v-else description="No comments found" class="min-h-50 justify-center" />

		<div class="mt-10 flex flex-col gap-2">
			<n-form-item label="Add Comment" :show-feedback="false">
				<n-input
					v-model:value.trim="newComment"
					placeholder="Enter your comment..."
					clearable
					type="textarea"
					:disabled="loading"
					:autosize="{ minRows: 3, maxRows: 10 }"
				/>
			</n-form-item>
			<div class="flex justify-end">
				<n-button :disabled="!newComment?.trim()" :loading type="primary" @click="addComment">
					Add Comment
				</n-button>
			</div>
		</div>
	</div>
</template>

<script setup lang="ts">
import type { Alert } from "@/types/alerts"
import type { CommentItem } from "@/types/comments"
import type { ApiError } from "@/types/common"
import { NButton, NEmpty, NFormItem, NInput, useMessage } from "naive-ui"
import { ref } from "vue"
import Api from "@/api"
import { useAuthStore } from "@/stores/auth"
import { getApiErrorMessage } from "@/utils"
import AlertComment from "./AlertComment.vue"

const { alert } = defineProps<{
	alert: Alert
}>()

const emit = defineEmits<{
	(e: "added", comment: CommentItem): void
	(e: "updated", comment: CommentItem): void
	(e: "deleted", commentId: number): void
}>()

const message = useMessage()
const authStore = useAuthStore()

const newComment = ref<string | null>(null)
const loading = ref(false)

async function addComment() {
	if (!alert || !newComment.value?.trim()) return

	loading.value = true

	try {
		const response = await Api.alerts.addComment({
			alertId: alert.id,
			comment: newComment.value.trim(),
			userName: authStore.userName || ""
		})

		emit("added", response.data.comment)
		newComment.value = ""
		message.success(response.data?.message || "Comment added successfully")
	} catch (err) {
		message.error(getApiErrorMessage(err as ApiError))
	} finally {
		loading.value = false
	}
}

function handleCommentUpdated(comment: CommentItem) {
	emit("updated", comment)
}

function handleCommentDeleted(commentId: number) {
	emit("deleted", commentId)
}
</script>
