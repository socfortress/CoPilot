<template>
	<div class="page">
		<AlertsList :highlight />
	</div>
</template>

<script setup lang="ts">
import AlertsList from "@/components/incidentManagement/alerts/AlertsList.vue"
import { onBeforeMount, ref } from "vue"
import { useRoute } from "vue-router"

const route = useRoute()

const highlight = ref<string | undefined>(undefined)

onBeforeMount(() => {
	if (route.query?.alert_id) {
		highlight.value = route.query.alert_id.toString() || undefined
	}
})
</script>
