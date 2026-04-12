<template>
	<div class="flex flex-col gap-2">
		<div v-if="caseData.comments?.length" class="flex flex-col gap-2">
			<CardEntity v-for="comment in caseData.comments" :key="comment.id" size="small" embedded>
				<template #header-main>{{ comment.user_name }}</template>
				<template #header-extra>{{ formatDate(comment.created_at, dFormats.datetime) }}</template>
				<template #default>{{ comment.comment }}</template>
			</CardEntity>
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
// TODO-CP: add edit/delete
import type { Case } from "@/types/cases"
import type { CommentItem } from "@/types/comments"
import type { ApiError } from "@/types/common"
import { NButton, NEmpty, NFormItem, NInput, useMessage } from "naive-ui"
import { ref } from "vue"
import Api from "@/api"
import CardEntity from "@/components/common/cards/CardEntity.vue"
import { useAuthStore } from "@/stores/auth"
import { useSettingsStore } from "@/stores/settings"
import { getApiErrorMessage } from "@/utils"
import { formatDate } from "@/utils/format"

const { caseData } = defineProps<{
	caseData: Case
}>()

const emit = defineEmits<{
	(e: "success", comment: CommentItem): void
}>()

const message = useMessage()
const authStore = useAuthStore()
const dFormats = useSettingsStore().dateFormat

const newComment = ref<string | null>(null)
const loading = ref(false)

async function addComment() {
	if (!caseData || !newComment.value?.trim()) return

	loading.value = true
	try {
		const response = await Api.cases.addComment({
			caseId: caseData.id,
			comment: newComment.value.trim(),
			userName: authStore.userName || ""
		})

		emit("success", response.data.comment)
		newComment.value = ""
	} catch (err) {
		message.error(getApiErrorMessage(err as ApiError))
	} finally {
		loading.value = false
	}
}
</script>
