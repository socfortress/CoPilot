<template>
	<div class="min-h-screen bg-gray-50">
		<!-- Header -->
		<header class="bg-white shadow">
			<div class="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
				<div class="flex h-16 justify-between">
					<div class="flex items-center">
						<router-link to="/" class="mr-4 text-indigo-600 hover:text-indigo-500">
							← Back to Dashboard
						</router-link>
						<h1 class="text-xl font-semibold">Security Cases</h1>
					</div>
					<div class="flex items-center space-x-4">
						<span class="text-sm text-gray-700">{{ user?.username }}</span>
						<button
							@click="logout"
							class="rounded-md bg-red-600 px-3 py-2 text-sm font-medium text-white hover:bg-red-700"
						>
							Logout
						</button>
					</div>
				</div>
			</div>
		</header>

		<!-- Main Content -->
		<main class="mx-auto max-w-7xl py-6 sm:px-6 lg:px-8">
			<div class="px-4 py-6 sm:px-0">
				<!-- Loading State -->
				<div v-if="loading" class="py-8 text-center">
					<div
						class="inline-flex items-center rounded-md bg-indigo-500 px-4 py-2 text-sm leading-6 font-semibold text-white shadow"
					>
						Loading cases...
					</div>
				</div>

				<!-- Error State -->
				<div v-else-if="error" class="rounded-md border border-red-200 bg-red-50 p-4">
					<div class="flex">
						<div class="ml-3">
							<h3 class="text-sm font-medium text-red-800">Error loading cases</h3>
							<div class="mt-2 text-sm text-red-700">
								{{ error }}
							</div>
						</div>
					</div>
				</div>

				<!-- Cases List -->
				<div v-else>
					<!-- Stats Cards -->
					<div class="mb-6 grid grid-cols-1 gap-4 md:grid-cols-4">
						<div class="overflow-hidden rounded-lg bg-white shadow">
							<div class="p-5">
								<div class="flex items-center">
									<div class="flex h-8 w-8 items-center justify-center rounded-md bg-red-500">
										<span class="text-sm font-medium text-white">O</span>
									</div>
									<div class="ml-3">
										<p class="text-sm font-medium text-gray-500">Open</p>
										<p class="text-lg font-semibold text-gray-900">{{ getCaseCount("open") }}</p>
									</div>
								</div>
							</div>
						</div>
						<div class="overflow-hidden rounded-lg bg-white shadow">
							<div class="p-5">
								<div class="flex items-center">
									<div class="flex h-8 w-8 items-center justify-center rounded-md bg-yellow-500">
										<span class="text-sm font-medium text-white">P</span>
									</div>
									<div class="ml-3">
										<p class="text-sm font-medium text-gray-500">In Progress</p>
										<p class="text-lg font-semibold text-gray-900">
											{{ getCaseCount("in_progress") }}
										</p>
									</div>
								</div>
							</div>
						</div>
						<div class="overflow-hidden rounded-lg bg-white shadow">
							<div class="p-5">
								<div class="flex items-center">
									<div class="flex h-8 w-8 items-center justify-center rounded-md bg-green-500">
										<span class="text-sm font-medium text-white">C</span>
									</div>
									<div class="ml-3">
										<p class="text-sm font-medium text-gray-500">Closed</p>
										<p class="text-lg font-semibold text-gray-900">{{ getCaseCount("closed") }}</p>
									</div>
								</div>
							</div>
						</div>
						<div class="overflow-hidden rounded-lg bg-white shadow">
							<div class="p-5">
								<div class="flex items-center">
									<div class="flex h-8 w-8 items-center justify-center rounded-md bg-gray-500">
										<span class="text-sm font-medium text-white">T</span>
									</div>
									<div class="ml-3">
										<p class="text-sm font-medium text-gray-500">Total</p>
										<p class="text-lg font-semibold text-gray-900">{{ cases.length }}</p>
									</div>
								</div>
							</div>
						</div>
					</div>

					<!-- Cases Table -->
					<div class="overflow-hidden bg-white shadow sm:rounded-md">
						<div class="px-4 py-5 sm:px-6">
							<h3 class="text-lg leading-6 font-medium text-gray-900">Security Cases</h3>
							<p class="mt-1 max-w-2xl text-sm text-gray-500">
								Security incident cases for your organization
							</p>
						</div>

						<div v-if="cases.length === 0" class="px-4 py-5 text-center text-gray-500 sm:px-6">
							No cases found
						</div>

						<ul v-else class="divide-y divide-gray-200">
							<li
								v-for="case_ in cases"
								:key="case_.id"
								class="cursor-pointer px-4 py-4 hover:bg-gray-50 sm:px-6"
								@click="viewCaseDetails(case_.id)"
							>
								<div class="flex items-center justify-between">
									<div class="flex items-center">
										<div
											class="mr-3 h-3 w-3 rounded-full"
											:class="{
												'bg-red-500': case_.case_status === 'open',
												'bg-yellow-500': case_.case_status === 'in_progress',
												'bg-green-500': case_.case_status === 'closed',
												'bg-gray-500': !case_.case_status
											}"
										></div>
										<div>
											<p class="text-sm font-medium text-gray-900 hover:text-indigo-600">
												{{ case_.case_name || "Unnamed Case" }}
											</p>
											<p class="text-sm text-gray-500">
												{{ case_.case_description || "No description available" }}
											</p>
											<p class="mt-1 text-xs text-gray-400">
												Created: {{ formatDate(case_.case_creation_time) }}
												<span v-if="case_.assigned_to">
													• Assigned to: {{ case_.assigned_to }}
												</span>
												<span v-if="case_.comments && case_.comments.length > 0">
													• {{ case_.comments.length }}
													{{ case_.comments.length === 1 ? "comment" : "comments" }}
												</span>
											</p>
										</div>
									</div>
									<div class="flex items-center space-x-2">
										<span
											class="inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium"
											:class="{
												'bg-red-100 text-red-800': case_.case_status === 'open',
												'bg-yellow-100 text-yellow-800': case_.case_status === 'in_progress',
												'bg-green-100 text-green-800': case_.case_status === 'closed',
												'bg-gray-100 text-gray-800': !case_.case_status
											}"
										>
											{{ case_.case_status || "Unknown" }}
										</span>
										<span
											v-if="case_.escalation_level"
											class="inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium"
											:class="{
												'bg-red-100 text-red-800': case_.escalation_level === 'high',
												'bg-yellow-100 text-yellow-800': case_.escalation_level === 'medium',
												'bg-blue-100 text-blue-800': case_.escalation_level === 'low'
											}"
										>
											{{ case_.escalation_level }}
										</span>
									</div>
								</div>
							</li>
						</ul>
					</div>

					<!-- Pagination (if needed) -->
					<div v-if="cases.length > 0" class="mt-6 flex justify-center">
						<button
							@click="refreshCases"
							class="rounded-md bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700"
						>
							Refresh
						</button>
					</div>
				</div>
			</div>
		</main>
	</div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed } from "vue"
import { useRouter } from "vue-router"
import { useAuthStore } from "@/stores/auth"
import { httpClient } from "@/utils/httpClient"

interface Case {
	id: number
	case_name: string
	case_description: string
	case_status: string
	case_creation_time: string
	assigned_to?: string
	escalation_level?: string
	customer_code?: string
	comments?: Array<{
		id: number
		comment: string
		user_name?: string
		created_at: string
	}>
}

const router = useRouter()
const authStore = useAuthStore()

const cases = ref<Case[]>([])
const loading = ref(false)
const error = ref("")

const user = computed(() => authStore.user)

const getCaseCount = (status: string) => {
	return cases.value.filter(case_ => case_.case_status === status).length
}

const formatDate = (dateString: string) => {
	if (!dateString) return "Unknown"
	try {
		return new Date(dateString).toLocaleDateString()
	} catch {
		return "Invalid date"
	}
}

const fetchCases = async () => {
	loading.value = true
	error.value = ""

	try {
		const response = await httpClient.get("/incidents/db_operations/cases")
		cases.value = response.data.cases || []
	} catch (err: any) {
		error.value = err.response?.data?.detail || "Failed to fetch cases"
		console.error("Failed to fetch cases:", err)
	} finally {
		loading.value = false
	}
}

const refreshCases = () => {
	fetchCases()
}

const viewCaseDetails = (caseId: number) => {
	router.push(`/cases/${caseId}`)
}

const logout = () => {
	authStore.logout()
	router.push("/login")
}

onMounted(() => {
	fetchCases()
})
</script>
