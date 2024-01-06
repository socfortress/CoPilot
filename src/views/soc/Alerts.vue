<template>
	<div class="page">
		<SocAlertsFullList :highlight="highlight" />
	</div>
</template>

<script setup lang="ts">
import SocAlertsFullList from "@/components/soc/SocAlerts/SocAlertsFullList.vue"
import { onBeforeMount, ref } from "vue"
import { useRoute } from "vue-router"

const route = useRoute()

const highlight = ref<string | undefined>(undefined)

onBeforeMount(() => {
	if (route.query?.id) {
		highlight.value = route.query.id.toString()
	}
})
</script>
