<template>
	<div class="mb-3 rounded-lg border border-gray-200 bg-white p-4">
		<div class="flex items-start justify-between">
			<div class="flex items-start space-x-3">
				<!-- User Avatar -->
				<div class="shrink-0">
					<div class="flex h-8 w-8 items-center justify-center rounded-full bg-indigo-500">
						<span class="text-sm font-medium text-white">
							{{ comment.user_name.charAt(0).toUpperCase() }}
						</span>
					</div>
				</div>

				<!-- Comment Content -->
				<div class="grow">
					<div class="mb-1 flex items-center space-x-2">
						<h4 class="text-sm font-medium text-gray-900">{{ comment.user_name }}</h4>
						<span class="text-xs text-gray-500">
							{{ formatTimeAgo(comment.created_at, dFormats.datetime) }}
						</span>
					</div>

					<!-- Edit Mode -->
					<div v-if="isEditing" class="space-y-2">
						<textarea
							v-model="editText"
							class="w-full rounded-md border border-gray-300 px-3 py-2 placeholder-gray-400 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 focus:outline-none sm:text-sm"
							rows="3"
							placeholder="Edit your comment..."
						></textarea>
						<div class="flex space-x-2">
							<button
								:disabled="!editText.trim() || isLoading"
								class="inline-flex items-center rounded border border-transparent bg-indigo-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-indigo-700 focus:ring-2 focus:ring-indigo-500 focus:ring-offset-2 focus:outline-none disabled:cursor-not-allowed disabled:opacity-50"
								@click="saveEdit"
							>
								<span v-if="isLoading" class="mr-1">
									<svg class="h-3 w-3 animate-spin" fill="none" viewBox="0 0 24 24">
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
								</span>
								Save
							</button>
							<button
								:disabled="isLoading"
								class="inline-flex items-center rounded border border-gray-300 bg-white px-3 py-1.5 text-xs font-medium text-gray-700 hover:bg-gray-50 focus:ring-2 focus:ring-indigo-500 focus:ring-offset-2 focus:outline-none disabled:cursor-not-allowed disabled:opacity-50"
								@click="cancelEdit"
							>
								Cancel
							</button>
						</div>
					</div>

					<!-- View Mode -->
					<div v-else class="text-sm whitespace-pre-wrap text-gray-700">{{ comment.comment }}</div>
				</div>
			</div>

			<!-- Actions -->
			<div v-if="canEdit && !isEditing" class="ml-2 flex items-center space-x-1">
				<button
					class="rounded p-1 text-gray-400 hover:text-gray-600 focus:ring-2 focus:ring-indigo-500 focus:ring-offset-2 focus:outline-none"
					title="Edit comment"
					@click="startEdit"
				>
					<svg class="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
						<path
							stroke-linecap="round"
							stroke-linejoin="round"
							stroke-width="2"
							d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z"
						></path>
					</svg>
				</button>
				<button
					class="rounded p-1 text-gray-400 hover:text-red-600 focus:ring-2 focus:ring-red-500 focus:ring-offset-2 focus:outline-none"
					title="Delete comment"
					@click="confirmDelete"
				>
					<svg class="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
						<path
							stroke-linecap="round"
							stroke-linejoin="round"
							stroke-width="2"
							d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"
						></path>
					</svg>
				</button>
			</div>
		</div>

		<!-- Error message -->
		<div v-if="error" class="mt-2 text-sm text-red-600">{{ error }}</div>
	</div>
</template>

<script setup lang="ts">
import type { CaseComment } from "@/api/cases"
import { computed, ref } from "vue"
import { CasesAPI } from "@/api/cases"
import { useAuthStore } from "@/stores/auth"
import { useSettingsStore } from "@/stores/settings"
import { formatTimeAgo } from "@/utils/format"

interface Props {
	comment: CaseComment
}

interface Emits {
	(e: "updated", comment: CaseComment): void
	(e: "deleted", commentId: number): void
}

const props = defineProps<Props>()
const emit = defineEmits<Emits>()

const authStore = useAuthStore()
const dFormats = useSettingsStore().dateFormat
const isEditing = ref(false)
const editText = ref("")
const isLoading = ref(false)
const error = ref("")

const canEdit = computed(() => {
	return authStore.user?.username === props.comment.user_name
})

function startEdit() {
	editText.value = props.comment.comment
	isEditing.value = true
	error.value = ""
}

function cancelEdit() {
	isEditing.value = false
	editText.value = ""
	error.value = ""
}

async function saveEdit() {
	if (!editText.value.trim()) return

	isLoading.value = true
	error.value = ""

	try {
		const response = await CasesAPI.updateCaseComment(
			props.comment.id,
			props.comment.case_id,
			editText.value.trim()
		)

		if (response.success) {
			emit("updated", response.comment)
			isEditing.value = false
			editText.value = ""
		} else {
			error.value = response.message || "Failed to update comment"
		}
	} catch (err: any) {
		error.value = err.response?.data?.detail || "Failed to update comment"
	} finally {
		isLoading.value = false
	}
}

function confirmDelete() {
	if (confirm("Are you sure you want to delete this comment?")) {
		deleteComment()
	}
}

async function deleteComment() {
	isLoading.value = true
	error.value = ""

	try {
		const response = await CasesAPI.deleteCaseComment(props.comment.id)

		if (response.success) {
			emit("deleted", props.comment.id)
		} else {
			error.value = response.message || "Failed to delete comment"
		}
	} catch (err: any) {
		error.value = err.response?.data?.detail || "Failed to delete comment"
	} finally {
		isLoading.value = false
	}
}
</script>
