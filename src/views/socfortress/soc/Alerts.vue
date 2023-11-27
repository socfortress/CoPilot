<template>
	<div class="page">
		<SocAlertsList :highlight="highlight" />
	</div>
</template>

<script setup lang="ts">
import SocAlertsList from "@/components/soc/SocAlertsList.vue"
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
