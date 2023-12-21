<template>
	<div class="page">
		<LogsList :userId="userId" />
	</div>
</template>

<script setup lang="ts">
import LogsList from "@/components/logs/LogsList.vue"
import { onBeforeMount, ref } from "vue"
import { useRoute } from "vue-router"

const route = useRoute()

const userId = ref<string | undefined>(undefined)

onBeforeMount(() => {
	if (route.query?.user_id) {
		userId.value = route.query.user_id.toString()
	}
})
</script>
