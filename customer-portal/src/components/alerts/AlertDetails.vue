<template>
	<n-spin :show="loadingDetails">
		<div class="min-h-50">
			<n-alert v-if="detailsError" title="Error" type="error" :description="detailsError" />

			<div v-else-if="alert" class="flex flex-col gap-4">
				<div class="grid grid-cols-1 gap-4 md:grid-cols-2">
					<n-card size="small">
						<template #header>
							<div class="text-secondary text-sm">Alert Name</div>
						</template>
						{{ alert.alert_name }}
					</n-card>
					<n-card size="small">
						<template #header>
							<div class="text-secondary text-sm">Status</div>
						</template>
						<n-tag :type="getStatusColor(alert.status)">
							{{ alert.status.replace("_", " ").toUpperCase() }}
						</n-tag>
					</n-card>
					<n-card size="small">
						<template #header>
							<div class="text-secondary text-sm">Source</div>
						</template>
						{{ alert.source }}
					</n-card>

					<n-card size="small">
						<template #header>
							<div class="text-secondary text-sm">Customer</div>
						</template>
						{{ alert.customer_code }}
					</n-card>

					<n-card size="small">
						<template #header>
							<div class="text-secondary text-sm">Created</div>
						</template>
						{{ formatDate(alert.alert_creation_time, dFormats.datetime) }}
					</n-card>

					<n-card v-if="alert.assigned_to" size="small">
						<template #header>
							<div class="text-secondary text-sm">Assigned To</div>
						</template>
						{{ alert.assigned_to }}
					</n-card>
				</div>

				<n-card v-if="alert.alert_description" size="small">
					<template #header>
						<div class="text-secondary text-sm">Description</div>
					</template>
					{{ alert.alert_description }}
				</n-card>

				<div v-if="alert.assets && alert.assets.length > 0">
					<label class="mb-2 block text-sm font-medium text-gray-700">Assets</label>
					<div class="rounded-lg bg-gray-50 p-4">
						<div
							v-for="asset in alert.assets"
							:key="asset.id"
							class="mb-3 border-b border-gray-200 pb-3 last:mb-0 last:border-b-0"
						>
							<div class="grid grid-cols-1 gap-2 text-sm md:grid-cols-3">
								<div>
									<span class="font-medium">Asset Name:</span>
									{{ asset.asset_name }}
								</div>
								<div>
									<span class="font-medium">Agent ID:</span>
									{{ asset.agent_id }}
								</div>
								<div v-if="asset.velociraptor_id">
									<span class="font-medium">Velociraptor ID:</span>
									{{ asset.velociraptor_id }}
								</div>
								<div>
									<span class="font-medium">Index:</span>
									{{ asset.index_name }}
								</div>
								<div>
									<span class="font-medium">Index ID:</span>
									{{ asset.index_id.substring(0, 20) }}...
								</div>
							</div>
						</div>
					</div>
				</div>

				<div v-else-if="alert.asset_name">
					<label class="block text-sm font-medium text-gray-700">Asset</label>
					<p class="mt-1 text-sm text-gray-900">{{ alert.asset_name }}</p>
				</div>

				<div v-if="alert.tags && alert.tags.length > 0">
					<label class="block text-sm font-medium text-gray-700">Tags</label>
					<div class="mt-1 flex flex-wrap gap-2">
						<span
							v-for="tag in alert.tags"
							:key="tag.id"
							class="inline-flex items-center rounded-full bg-blue-100 px-2.5 py-0.5 text-xs font-medium text-blue-800"
						>
							{{ tag.tag }}
						</span>
					</div>
				</div>

				<div v-else-if="alert.tag && alert.tag.length > 0">
					<label class="block text-sm font-medium text-gray-700">Tags</label>
					<div class="mt-1 flex flex-wrap gap-2">
						<span
							v-for="tag in alert.tag"
							:key="tag"
							class="inline-flex items-center rounded-full bg-blue-100 px-2.5 py-0.5 text-xs font-medium text-blue-800"
						>
							{{ tag }}
						</span>
					</div>
				</div>

				<div v-if="alert.linked_cases && alert.linked_cases.length > 0">
					<label class="mb-2 block text-sm font-medium text-gray-700">Linked Cases</label>
					<div class="rounded-lg bg-gray-50 p-4">
						<div
							v-for="linkedCase in alert.linked_cases"
							:key="linkedCase.id"
							class="mb-3 border-b border-gray-200 pb-3 last:mb-0 last:border-b-0"
						>
							<div class="flex items-start justify-between">
								<div class="flex-1">
									<h4 class="text-sm font-medium text-gray-900">{{ linkedCase.case_name }}</h4>
									<p class="mt-1 text-xs text-gray-600">{{ linkedCase.case_description }}</p>
									<div class="mt-2 flex items-center space-x-4 text-xs text-gray-500">
										<span>Case #{{ linkedCase.id }}</span>
										<span>
											Created: {{ formatDate(linkedCase.case_creation_time, dFormats.datetime) }}
										</span>
										<span v-if="linkedCase.assigned_to">
											Assigned to: {{ linkedCase.assigned_to }}
										</span>
									</div>
								</div>
								<span
									class="inline-flex items-center rounded-full px-2 py-1 text-xs font-medium"
									:class="{
										'bg-red-100 text-red-800': linkedCase.case_status === 'OPEN',
										'bg-yellow-100 text-yellow-800': linkedCase.case_status === 'IN_PROGRESS',
										'bg-green-100 text-green-800': linkedCase.case_status === 'CLOSED'
									}"
								>
									{{ linkedCase.case_status.replace("_", " ").toUpperCase() }}
								</span>
							</div>
						</div>
					</div>
				</div>

				<div v-else-if="alert.case_ids && alert.case_ids.length > 0">
					<label class="block text-sm font-medium text-gray-700">Linked Cases</label>
					<div class="mt-1 flex flex-wrap gap-2">
						<span
							v-for="caseId in alert.case_ids"
							:key="caseId"
							class="inline-flex items-center rounded-full bg-purple-100 px-2.5 py-0.5 text-xs font-medium text-purple-800"
						>
							Case #{{ caseId }}
						</span>
					</div>
				</div>

				<div v-if="alert.iocs && alert.iocs.length > 0">
					<label class="mb-2 block text-sm font-medium text-gray-700">Indicators of Compromise (IoCs)</label>
					<div class="rounded-lg bg-gray-50 p-4">
						<div
							v-for="ioc in alert.iocs"
							:key="ioc.id"
							class="mb-3 border-b border-gray-200 pb-3 last:mb-0 last:border-b-0"
						>
							<div class="grid grid-cols-1 gap-2 text-sm md:grid-cols-3">
								<div>
									<span class="font-medium">Value:</span>
									<code class="rounded bg-gray-100 px-1 text-xs">{{ ioc.ioc_value }}</code>
								</div>
								<div>
									<span class="font-medium">Type:</span>
									{{ ioc.ioc_type }}
								</div>
								<div>
									<span class="font-medium">Description:</span>
									{{ ioc.ioc_description }}
								</div>
							</div>
						</div>
					</div>
				</div>

				<div>
					<label class="mb-2 block text-sm font-medium text-gray-700">
						Comments
						<span v-if="alert.comments && alert.comments.length > 0" class="font-normal text-gray-500">
							({{ alert.comments.length }})
						</span>
					</label>

					<div
						v-if="alert.comments && alert.comments.length > 0"
						class="mb-4 max-h-64 overflow-y-auto rounded-lg bg-gray-50 p-4"
					>
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

					<div v-else class="mb-4 rounded-lg bg-gray-50 p-4 text-center">
						<p class="text-sm text-gray-500">No comments yet</p>
					</div>

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
								:disabled="!newComment.trim() || isAddingComment"
								class="inline-flex items-center rounded-md border border-transparent bg-indigo-600 px-4 py-2 text-sm font-medium text-white shadow-sm hover:bg-indigo-700 focus:ring-2 focus:ring-indigo-500 focus:ring-offset-2 focus:outline-none disabled:cursor-not-allowed disabled:opacity-50"
								@click="addComment"
							>
								<svg
									v-if="isAddingComment"
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
								{{ isAddingComment ? "Adding..." : "Add Comment" }}
							</button>
						</div>
					</div>
				</div>
			</div>
		</div>
	</n-spin>
</template>

<script setup lang="ts">
import type { TagColor } from "naive-ui/es/tag/src/common-props"
import type { Alert } from "@/api/endpoints/alerts"
import type { ApiError } from "@/types/common"
import { NAlert, NCard, NSpin, NTag, useMessage } from "naive-ui"
import { ref, watch } from "vue"
import Api from "@/api"
import Icon from "@/components/common/Icon.vue"
import { useSettingsStore } from "@/stores/settings"
import { getApiErrorMessage, getStatusColor } from "@/utils"
import { formatDate } from "@/utils/format"

const props = defineProps<{
	alertId: number | null
}>()

const message = useMessage()
const dFormats = useSettingsStore().dateFormat

const alert = ref<Alert | null>(null)
const detailsError = ref<string | null>(null)
const loadingDetails = ref(false)
const newComment = ref("")
const isAddingComment = ref(false)

async function loadAlertDetails() {
	if (props.alertId === null) return

	loadingDetails.value = true
	detailsError.value = null

	try {
		const response = await Api.alerts.getAlert(props.alertId)
		alert.value = response.data.alerts[0] || null
		if (!alert.value) {
			detailsError.value = "Alert not found."
		}
	} catch (err) {
		detailsError.value = getApiErrorMessage(err as ApiError)
	} finally {
		loadingDetails.value = false
	}
}

async function addComment() {
	if (!alert.value || !newComment.value.trim()) return

	isAddingComment.value = true
	try {
		const response = await Api.alerts.addComment({
			alert_id: alert.value.id,
			comment: newComment.value.trim(),
			user_name: "Customer User"
		})

		if (!alert.value.comments) {
			alert.value.comments = []
		}
		alert.value.comments.push(response.data.comment)
		newComment.value = ""
	} catch (err) {
		message.error(getApiErrorMessage(err as ApiError))
	} finally {
		isAddingComment.value = false
	}
}

watch(
	() => props.alertId,
	async newAlertId => {
		newComment.value = ""
		alert.value = null
		detailsError.value = null

		if (newAlertId !== null) {
			await loadAlertDetails()
		}
	},
	{ immediate: true }
)
</script>
