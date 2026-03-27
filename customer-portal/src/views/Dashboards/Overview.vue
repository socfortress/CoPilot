<template>
	<div class="min-h-screen bg-gray-50">
		<!-- Header -->
		<header class="border-b bg-white shadow-sm">
			<div class="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
				<div class="flex h-16 justify-between">
					<div class="flex items-center">
						<div class="mr-3 min-h-8">
							<img
								v-if="portalLogo && showLogo"
								class="h-8 w-auto"
								:src="portalLogo"
								:alt="portalTitle"
								@error="showLogo = false"
							/>
						</div>
						<h1 class="text-xl font-semibold text-gray-900">{{ portalTitle }}</h1>
						<nav class="ml-8 flex space-x-8">
							<router-link
								to="/"
								class="rounded-md px-3 py-2 text-sm font-medium text-gray-500 hover:text-gray-900"
							>
								Overview
							</router-link>
							<router-link
								to="/alerts"
								class="rounded-md px-3 py-2 text-sm font-medium text-gray-500 hover:text-gray-900"
							>
								Alerts
							</router-link>
							<router-link
								to="/cases"
								class="rounded-md px-3 py-2 text-sm font-medium text-gray-500 hover:text-gray-900"
							>
								Cases
							</router-link>
							<router-link
								to="/agents"
								class="rounded-md px-3 py-2 text-sm font-medium text-gray-500 hover:text-gray-900"
							>
								Agents
							</router-link>
							<router-link
								to="/event-search"
								class="rounded-md px-3 py-2 text-sm font-medium text-gray-500 hover:text-gray-900"
							>
								Event Search
							</router-link>
							<router-link
								to="/dashboards"
								class="rounded-md border-b-2 border-indigo-600 px-3 py-2 text-sm font-medium text-indigo-600"
							>
								Dashboards
							</router-link>
						</nav>
					</div>
					<div class="flex items-center space-x-4">
						<div class="text-sm text-gray-700">
							Welcome,
							<span class="font-medium">{{ username }}</span>
						</div>
						<button
							class="rounded-md bg-red-600 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-red-700"
							@click="logout"
						>
							Logout
						</button>
					</div>
				</div>
			</div>
		</header>

		<div class="mx-auto max-w-7xl px-4 py-6 sm:px-6 lg:px-8">
			<DashboardViewer :dashboard-id />
		</div>
	</div>
</template>

<script setup lang="ts">
import { computed, ref } from "vue"
import { useRoute, useRouter } from "vue-router"
import DashboardViewer from "@/components/dashboards/DashboardViewer.vue"
import { usePortalSettingsStore } from "@/stores/portalSettings"

const route = useRoute()
const router = useRouter()
const portalSettingsStore = usePortalSettingsStore()

const showLogo = ref(true)

const username = computed(() => {
	try {
		const user = JSON.parse(localStorage.getItem("customer-portal-user") || "{}")
		return user.username || "User"
	} catch {
		return "User"
	}
})
const portalTitle = computed(() => portalSettingsStore.portalTitle || "Customer Portal")
const portalLogo = computed(() => portalSettingsStore.portalLogo)

function logout() {
	localStorage.removeItem("customer-portal-auth-token")
	localStorage.removeItem("customer-portal-user")
	router.push("/login")
}

const dashboardId = computed(() => Number(route.params.id))
</script>
