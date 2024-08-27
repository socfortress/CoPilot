<template>
	<div class="flex flex-col gap-6">
		<template v-if="commentsList.length">
			<AlertCommentItem :comment embedded v-for="comment of commentsList" :key="comment.id" />
		</template>
		<template v-else>
			<n-empty description="No comments found" class="justify-center h-48" />
		</template>
		<n-spin :show="submitting">
			<div class="comment-form mt-6 flex flex-col gap-3">
				<div class="editor-box">
					<n-input
						placeholder="Write a new comment..."
						type="textarea"
						v-model:value="commentMessage"
						:autosize="{
							minRows: 3,
							maxRows: 10
						}"
					/>
				</div>
				<div class="tool-box flex gap-2 justify-end">
					<n-button secondary @click="reset()" :disabled="submitting">Reset</n-button>
					<n-button
						type="primary"
						@click="submit()"
						:disabled="!trimmedValue || submitting"
						:loading="submitting"
					>
						<template #icon><Icon :name="CommentsIcon" /></template>
						Send comment
					</n-button>
				</div>
			</div>
		</n-spin>
	</div>
</template>

<script setup lang="ts">
import { computed, ref, toRefs } from "vue"
import { NEmpty, NInput, NButton, NSpin, useMessage } from "naive-ui"
import AlertCommentItem from "./AlertComment.vue"
import Icon from "@/components/common/Icon.vue"
import type { AlertComment } from "@/types/incidentManagement/alerts.d"
import Api from "@/api"
import { useAuthStore } from "@/stores/auth"
import _trim from "lodash/trim"

const props = defineProps<{ comments: AlertComment[]; alertId: number }>()
const { comments, alertId } = toRefs(props)

const emit = defineEmits<{
	(e: "updated", value: AlertComment[]): void
}>()

const CommentsIcon = "carbon:chat"
const commentsList = ref<AlertComment[]>(comments.value)
const commentMessage = ref<string | null>(null)
const submitting = ref(false)
const message = useMessage()
const authStore = useAuthStore()
const trimmedValue = computed(() => _trim(commentMessage.value || ""))

function reset() {
	commentMessage.value = ""
}

function submit() {
	if (trimmedValue.value) {
		submitting.value = true

		Api.incidentManagement
			.newAlertComment({
				alert_id: alertId.value,
				comment: trimmedValue.value,
				created_at: new Date(),
				user_name: authStore.userName
			})
			.then(res => {
				if (res.data.success) {
					reset()
					commentsList.value.push(res.data.comment)
					emit("updated", commentsList.value)
				} else {
					message.warning(res.data?.message || "An error occurred. Please try again later.")
				}
			})
			.catch(err => {
				message.error(err.response?.data?.message || "An error occurred. Please try again later.")
			})
			.finally(() => {
				submitting.value = false
			})
	}
}
</script>
