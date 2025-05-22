<template>
	<div class="page">
		<CasesList :highlight />
	</div>
</template>

<script setup lang="ts">
import { onBeforeMount, ref } from "vue"
import { useRoute } from "vue-router"
import CasesList from "@/components/incidentManagement/cases/CasesList.vue"

const route = useRoute()

const highlight = ref<string | undefined>(undefined)

onBeforeMount(() => {
	if (route.query?.case_id) {
		highlight.value = route.query.case_id.toString() || undefined
	}
})
</script>
