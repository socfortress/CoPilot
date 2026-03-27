<template>
	<div class="space-y-4">
		<!-- Header -->
		<div class="flex items-center justify-between">
			<h3 class="text-lg font-medium text-gray-900">Comments</h3>
			<span class="text-sm text-gray-500">
				{{ comments.length }} {{ comments.length === 1 ? "comment" : "comments" }}
			</span>
		</div>

		<!-- New Comment Form -->
		<div class="rounded-lg border border-gray-200 bg-gray-50 p-4">
			<div class="space-y-3">
				<textarea
					v-model="newComment"
					class="w-full rounded-md border border-gray-300 px-3 py-2 placeholder-gray-400 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 focus:outline-none sm:text-sm"
					rows="3"
					placeholder="Add a comment..."
				></textarea>
				<div class="flex justify-end">
					<button
						@click="addComment"
						:disabled="!newComment.trim() || isSubmitting"
						class="inline-flex items-center rounded-md border border-transparent bg-indigo-600 px-4 py-2 text-sm font-medium text-white shadow-sm hover:bg-indigo-700 focus:ring-2 focus:ring-indigo-500 focus:ring-offset-2 focus:outline-none disabled:cursor-not-allowed disabled:opacity-50"
					>
						<span v-if="isSubmitting" class="mr-2">
							<svg class="h-4 w-4 animate-spin" fill="none" viewBox="0 0 24 24">
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
						Add Comment
					</button>
				</div>
			</div>

			<!-- Error message -->
			<div v-if="error" class="mt-2 text-sm text-red-600">{{ error }}</div>
		</div>

		<!-- Comments List -->
		<div v-if="comments.length === 0" class="py-8 text-center text-gray-500">
			<svg class="mx-auto mb-4 h-12 w-12 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
				<path
					stroke-linecap="round"
					stroke-linejoin="round"
					stroke-width="2"
					d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z"
				></path>
			</svg>
			<p>No comments yet</p>
			<p class="text-sm">Be the first to add a comment to this case.</p>
		</div>

		<div v-else class="space-y-3">
			<CaseComment
				v-for="comment in sortedComments"
				:key="comment.id"
				:comment="comment"
				@updated="handleCommentUpdated"
				@deleted="handleCommentDeleted"
			/>
		</div>
	</div>
</template>

<script setup lang="ts">
import { ref, computed } from "vue"
import CaseComment from "./CaseComment.vue"
import type { CaseComment as CaseCommentType } from "@/api/cases"
import { CasesAPI } from "@/api/cases"

interface Props {
	caseId: number
	comments: CaseCommentType[]
}

interface Emits {
	(e: "commentsUpdated", comments: CaseCommentType[]): void
}

const props = defineProps<Props>()
const emit = defineEmits<Emits>()

const newComment = ref("")
const isSubmitting = ref(false)
const error = ref("")

const sortedComments = computed(() => {
	return [...props.comments].sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime())
})

const addComment = async () => {
	if (!newComment.value.trim()) return

	isSubmitting.value = true
	error.value = ""

	try {
		const response = await CasesAPI.createCaseComment(props.caseId, newComment.value.trim())

		if (response.success) {
			const updatedComments = [...props.comments, response.comment]
			emit("commentsUpdated", updatedComments)
			newComment.value = ""
		} else {
			error.value = response.message || "Failed to add comment"
		}
	} catch (err: any) {
		error.value = err.response?.data?.detail || "Failed to add comment"
	} finally {
		isSubmitting.value = false
	}
}

const handleCommentUpdated = (updatedComment: CaseCommentType) => {
	const updatedComments = props.comments.map(comment => (comment.id === updatedComment.id ? updatedComment : comment))
	emit("commentsUpdated", updatedComments)
}

const handleCommentDeleted = (commentId: number) => {
	const updatedComments = props.comments.filter(comment => comment.id !== commentId)
	emit("commentsUpdated", updatedComments)
}
</script>
