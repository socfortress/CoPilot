<template>
	<div class="flex flex-col gap-6">
		<template v-if="commentsList.length">
			<AlertCommentItem
				v-for="comment of commentsList"
				:key="comment.id"
				:comment
				embedded
				@deleted="removeComment(comment)"
				@updated="updateComment($event)"
			/>
		</template>
		<template v-else>
			<n-empty description="No comments found" class="h-48 justify-center" />
		</template>
		<n-spin :show="submitting">
			<div class="comment-form mt-6 flex flex-col gap-3">
				<div class="editor-box">
					<n-input
						v-model:value="commentMessage"
						placeholder="Write a new comment..."
						type="textarea"
						:autosize="{
							minRows: 3,
							maxRows: 10
						}"
					/>
				</div>
				<div class="tool-box flex flex-wrap items-center justify-between gap-2">
					<n-button quaternary :disabled="submitting" :loading="reloading" @click="reload()">
						<template #icon>
							<Icon :name="ReloadIcon" />
						</template>
						Reload comments
					</n-button>
					<div class="flex gap-2">
						<n-button secondary :disabled="submitting" @click="reset()">Reset</n-button>
						<n-button
							type="primary"
							:disabled="!trimmedValue || submitting"
							:loading="submitting"
							@click="submit()"
						>
							<template #icon>
								<Icon :name="CommentsIcon" />
							</template>
							Send comment
						</n-button>
					</div>
				</div>
			</div>
		</n-spin>
	</div>
</template>

<script setup lang="ts">
import type { ApiError } from "@/types/common"
import type { AlertComment } from "@/types/incidentManagement/alerts"
import _trim from "lodash/trim"
import { NButton, NEmpty, NInput, NSpin, useMessage } from "naive-ui"
import { computed, ref, toRefs, watch } from "vue"
import Api from "@/api"
import Icon from "@/components/common/Icon.vue"
import { useAuthStore } from "@/stores/auth"
import { getApiErrorMessage } from "@/utils"
import AlertCommentItem from "./AlertComment.vue"

const props = defineProps<{ comments: AlertComment[]; alertId: number }>()
const emit = defineEmits<{
	(e: "updated", value: AlertComment[]): void
}>()

const { comments, alertId } = toRefs(props)

const CommentsIcon = "carbon:chat"
const ReloadIcon = "carbon:renew"
const commentsList = ref<AlertComment[]>(comments.value)
const commentMessage = ref<string | null>(null)
const submitting = ref(false)
const reloading = ref(false)
const message = useMessage()
const authStore = useAuthStore()
const trimmedValue = computed(() => _trim(commentMessage.value || ""))

// A comment can be added from outside this list (the verdict dialog posts one), which
// replaces the alert's comments array — pick the new array up instead of the stale copy.
watch(comments, value => {
	commentsList.value = value
})

function reset() {
	commentMessage.value = ""
}

function updateComment(newComment: AlertComment) {
	const comment = commentsList.value.find(o => o.id === newComment.id)
	if (comment) {
		comment.created_at = newComment.created_at
		comment.comment = newComment.comment
	}
}

function removeComment(comment: AlertComment) {
	commentsList.value.splice(
		commentsList.value.findIndex(o => o.id === comment.id),
		1
	)
}

// There is no comments-only endpoint: the alert fetch is the source of truth, and its
// comments array is what this list already renders, so re-reading it is the reload.
function reload() {
	reloading.value = true

	Api.incidentManagement.alerts
		.getAlert(alertId.value)
		.then(res => {
			if (res.data.success) {
				commentsList.value = res.data.alerts?.[0]?.comments || []
				emit("updated", commentsList.value)
			} else {
				message.warning(res.data?.message || "An error occurred. Please try again later.")
			}
		})
		.catch(err => {
			message.error(getApiErrorMessage(err as ApiError) || "An error occurred. Please try again later.")
		})
		.finally(() => {
			reloading.value = false
		})
}

function submit() {
	if (trimmedValue.value) {
		submitting.value = true

		Api.incidentManagement.alerts
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
				message.error(getApiErrorMessage(err as ApiError) || "An error occurred. Please try again later.")
			})
			.finally(() => {
				submitting.value = false
			})
	}
}
</script>
