<template>
	<div class="page @container flex flex-col gap-6">
		<DashboardViewer v-if="dashboardId" :dashboard-id />
	</div>
</template>

<script setup lang="ts">
import { useRoute } from "vue-router"
import DashboardViewer from "@/components/dashboards/DashboardViewer.vue"
import { toNumber } from "@/utils/format"

const route = useRoute()
const dashboardId = route.params.id ? toNumber(route.params.id as string) : null
</script>
