<template>
	<div class="page">
		<LogsList :user-id="userId" />
	</div>
</template>

<script setup lang="ts">
import { onBeforeMount, ref } from "vue"
import { useRoute } from "vue-router"
import LogsList from "@/components/logs/LogsList.vue"

const route = useRoute()

const userId = ref<string | undefined>(undefined)

onBeforeMount(() => {
	if (route.query?.user_id) {
		userId.value = route.query.user_id.toString()
	}
})
</script>
