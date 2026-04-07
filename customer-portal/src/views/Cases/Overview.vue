<template>
	<div class="min-h-screen bg-gray-50">
		<!-- Main Content -->
		<main class="mx-auto max-w-7xl py-6 sm:px-6 lg:px-8">
			<div class="px-4 py-6 sm:px-0">
				<!-- Loading State -->
				<div v-if="loading" class="py-8 text-center">
					<div
						class="inline-flex items-center rounded-md bg-indigo-500 px-4 py-2 text-sm leading-6 font-semibold text-white shadow"
					>
						Loading case details...
					</div>
				</div>

				<!-- Error State -->
				<div v-else-if="error" class="rounded-md border border-red-200 bg-red-50 p-4">
					<div class="flex">
						<div class="ml-3">
							<h3 class="text-sm font-medium text-red-800">Error loading case</h3>
							<div class="mt-2 text-sm text-red-700">
								{{ error }}
							</div>
						</div>
					</div>
				</div>

				<!-- Case Details -->
				<div v-else-if="caseData" class="space-y-6">
					<!-- Case Header -->
					<div class="overflow-hidden bg-white shadow sm:rounded-lg">
						<div class="px-4 py-5 sm:px-6">
							<div class="flex items-center justify-between">
								<div>
									<h3 class="text-lg leading-6 font-medium text-gray-900">
										{{ caseData.case_name || "Unnamed Case" }}
									</h3>
									<p class="mt-1 max-w-2xl text-sm text-gray-500">Case #{{ caseData.id }}</p>
								</div>
								<div class="flex items-center space-x-2">
									<span
										class="inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium"
										:class="{
											'bg-red-100 text-red-800': caseData.case_status === 'OPEN',
											'bg-yellow-100 text-yellow-800': caseData.case_status === 'IN_PROGRESS',
											'bg-green-100 text-green-800': caseData.case_status === 'CLOSED',
											'bg-gray-100 text-gray-800': !caseData.case_status
										}"
									>
										{{ caseData.case_status || "Unknown" }}
									</span>
								</div>
							</div>
						</div>
						<div class="border-t border-gray-200 px-4 py-5 sm:p-0">
							<dl class="sm:divide-y sm:divide-gray-200">
								<div class="py-4 sm:grid sm:grid-cols-3 sm:gap-4 sm:px-6 sm:py-5">
									<dt class="text-sm font-medium text-gray-500">Description</dt>
									<dd class="mt-1 text-sm text-gray-900 sm:col-span-2 sm:mt-0">
										{{ caseData.case_description || "No description available" }}
									</dd>
								</div>
								<div class="py-4 sm:grid sm:grid-cols-3 sm:gap-4 sm:px-6 sm:py-5">
									<dt class="text-sm font-medium text-gray-500">Created</dt>
									<dd class="mt-1 text-sm text-gray-900 sm:col-span-2 sm:mt-0">
										{{ formatDate(caseData.case_creation_time, dFormats.datetime) }}
									</dd>
								</div>
								<div class="py-4 sm:grid sm:grid-cols-3 sm:gap-4 sm:px-6 sm:py-5">
									<dt class="text-sm font-medium text-gray-500">Assigned to</dt>
									<dd class="mt-1 text-sm text-gray-900 sm:col-span-2 sm:mt-0">
										{{ caseData.assigned_to || "Unassigned" }}
									</dd>
								</div>
								<div
									v-if="caseData.customer_code"
									class="py-4 sm:grid sm:grid-cols-3 sm:gap-4 sm:px-6 sm:py-5"
								>
									<dt class="text-sm font-medium text-gray-500">Customer</dt>
									<dd class="mt-1 text-sm text-gray-900 sm:col-span-2 sm:mt-0">
										{{ caseData.customer_code }}
									</dd>
								</div>
							</dl>
						</div>
					</div>

					<!-- Alerts Section -->
					<div
						v-if="caseData.alerts && caseData.alerts.length > 0"
						class="overflow-hidden bg-white shadow sm:rounded-lg"
					>
						<div class="px-4 py-5 sm:px-6">
							<h3 class="text-lg leading-6 font-medium text-gray-900">
								Related Alerts ({{ caseData.alerts.length }})
							</h3>
						</div>
						<div class="border-t border-gray-200">
							<ul class="divide-y divide-gray-200">
								<li v-for="alert in caseData.alerts" :key="alert.id" class="px-4 py-4 sm:px-6">
									<div class="flex items-center justify-between">
										<div>
											<p class="text-sm font-medium text-gray-900">
												{{ alert.alert_name || "Unnamed Alert" }}
											</p>
											<p class="text-sm text-gray-500">Alert #{{ alert.id }}</p>
										</div>
										<span
											class="inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium"
											:class="{
												'bg-red-100 text-red-800': alert.status === 'OPEN',
												'bg-yellow-100 text-yellow-800': alert.status === 'IN_PROGRESS',
												'bg-green-100 text-green-800': alert.status === 'CLOSED',
												'bg-gray-100 text-gray-800': !alert.status
											}"
										>
											{{ alert.status || "Unknown" }}
										</span>
									</div>
								</li>
							</ul>
						</div>
					</div>

					<!-- Comments Section -->
					<div class="overflow-hidden bg-white shadow sm:rounded-lg">
						<div class="px-4 py-5 sm:px-6">
							<CaseCommentsList
								:case-id="caseData.id"
								:comments
								@comments-updated="handleCommentsUpdated"
							/>
						</div>
					</div>
				</div>
			</div>
		</main>
	</div>
</template>

<script setup lang="ts">
import type { Case, CaseComment } from "@/api/endpoints/cases"
import { onBeforeMount, ref } from "vue"
import { useRoute } from "vue-router"
import Api from "@/api"
import CaseCommentsList from "@/components/CaseCommentsList.vue"
import { useSettingsStore } from "@/stores/settings"
import { formatDate } from "@/utils/format"

const route = useRoute()

const caseData = ref<Case | null>(null)
const comments = ref<CaseComment[]>([])
const loading = ref(false)
const error = ref("")
const dFormats = useSettingsStore().dateFormat

async function fetchCaseDetails() {
	const caseId = Number(route.params.id)
	if (!caseId) {
		error.value = "Invalid case ID"
		return
	}

	loading.value = true
	error.value = ""

	try {
		const response = await Api.cases.getCase(caseId)
		if (response.data.success && response.data.cases.length > 0) {
			caseData.value = response.data.cases[0]
			comments.value = response.data.cases[0].comments || []
		} else {
			error.value = "Case not found"
		}
	} catch (err: any) {
		error.value = err.response?.data?.detail || "Failed to fetch case details"
		console.error("Failed to fetch case details:", err)
	} finally {
		loading.value = false
	}
}

function handleCommentsUpdated(updatedComments: CaseComment[]) {
	comments.value = updatedComments
	// Also update the case data if it has comments
	if (caseData.value) {
		caseData.value.comments = updatedComments
	}
}

onBeforeMount(() => {
	fetchCaseDetails()
})
</script>
