<template>
	<div class="page">
		<DashboardViewer :dashboard-id="dashboardId" />
	</div>
</template>

<script setup lang="ts">
import { computed } from "vue"
import { useRoute } from "vue-router"
import DashboardViewer from "@/components/dashboards/DashboardViewer.vue"

const route = useRoute()
const dashboardId = computed(() => Number(route.params.id))
</script>
