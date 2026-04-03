<template>
	<div class="min-h-screen bg-gray-50">
		<div class="mx-auto max-w-7xl px-4 py-6 sm:px-6 lg:px-8">
			<DashboardViewer :dashboard-id />
		</div>
	</div>
</template>

<script setup lang="ts">
import { useRoute } from "vue-router"
import DashboardViewer from "@/components/dashboards/DashboardViewer.vue"

const route = useRoute()

const dashboardId = Number(route.params.id)
</script>
