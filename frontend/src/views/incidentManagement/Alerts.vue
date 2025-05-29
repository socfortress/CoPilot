<template>
	<div class="page">
		<AlertsList :highlight />
	</div>
</template>

<script setup lang="ts">
import { onBeforeMount, ref } from "vue"
import { useRoute } from "vue-router"
import AlertsList from "@/components/incidentManagement/alerts/AlertsList.vue"

const route = useRoute()

const highlight = ref<string | undefined>(undefined)

onBeforeMount(() => {
	if (route.query?.alert_id) {
		highlight.value = route.query.alert_id.toString() || undefined
	}
})
</script>
