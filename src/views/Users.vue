<template>
	<div class="page">
		<UsersList :highlight="highlight" />
	</div>
</template>

<script setup lang="ts">
import UsersList from "@/components/users/UsersList.vue"
import { onBeforeMount, ref } from "vue"
import { useRoute } from "vue-router"

const route = useRoute()

const highlight = ref<string | undefined>(undefined)

onBeforeMount(() => {
	if (route.query?.user_id) {
		highlight.value = route.query.user_id.toString()
	}
})
</script>
