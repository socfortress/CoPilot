<template>
	<div class="flex flex-col gap-2">
		<div v-if="alert.comments?.length" class="mb-4 max-h-64 overflow-y-auto rounded-lg bg-gray-50 p-4">
			<div
				v-for="comment in alert.comments"
				:key="comment.id"
				class="mb-3 border-b border-gray-200 pb-3 last:mb-0 last:border-b-0"
			>
				<div class="mb-2 flex items-start justify-between">
					<span class="text-sm font-medium text-gray-900">{{ comment.user_name }}</span>
					<span class="text-xs text-gray-500">
						{{ formatDate(comment.created_at, dFormats.datetime) }}
					</span>
				</div>
				<p class="text-sm whitespace-pre-wrap text-gray-700">{{ comment.comment }}</p>
			</div>
		</div>

		<n-empty v-else description="No comments found" class="min-h-50 justify-center" />

		<div class="rounded-lg border bg-white p-4">
			<label class="mb-2 block text-sm font-medium text-gray-700">Add Comment</label>
			<textarea
				v-model="newComment"
				placeholder="Enter your comment..."
				rows="3"
				class="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-indigo-500 focus:ring-2 focus:ring-indigo-500 focus:outline-none"
			></textarea>
			<div class="mt-3 flex justify-end">
				<button
					:disabled="!newComment?.trim() || loading"
					class="inline-flex items-center rounded-md border border-transparent bg-indigo-600 px-4 py-2 text-sm font-medium text-white shadow-sm hover:bg-indigo-700 focus:ring-2 focus:ring-indigo-500 focus:ring-offset-2 focus:outline-none disabled:cursor-not-allowed disabled:opacity-50"
					@click="addComment"
				>
					<svg
						v-if="loading"
						class="mr-2 -ml-1 h-4 w-4 animate-spin text-white"
						xmlns="http://www.w3.org/2000/svg"
						fill="none"
						viewBox="0 0 24 24"
					>
						<circle
							class="opacity-25"
							cx="12"
							cy="12"
							r="10"
							stroke="currentColor"
							stroke-width="4"
						></circle>
						<path
							class="opacity-75"
							fill="currentColor"
							d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
						></path>
					</svg>
					{{ loading ? "Adding..." : "Add Comment" }}
				</button>
			</div>
		</div>
	</div>
</template>

<script setup lang="ts">
import type { Alert, AlertComment } from "@/api/endpoints/alerts"
import type { ApiError } from "@/types/common"
import { NEmpty, useMessage } from "naive-ui"
import { ref } from "vue"
import Api from "@/api"
import { useSettingsStore } from "@/stores/settings"
import { getApiErrorMessage } from "@/utils"
import { formatDate } from "@/utils/format"

const { alert } = defineProps<{
	alert: Alert
}>()

const emit = defineEmits<{
	(e: "success", comment: AlertComment): void
}>()

const message = useMessage()
const dFormats = useSettingsStore().dateFormat

const newComment = ref<string | null>(null)
const loading = ref(false)

async function addComment() {
	if (!alert || !newComment.value?.trim()) return

	loading.value = true
	try {
		const response = await Api.alerts.addComment({
			alert_id: alert.id,
			comment: newComment.value.trim(),
			user_name: "Customer User"
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
