<template>
	<div class="page flex flex-col gap-8">
		<UsersList :highlight />

		<AllowedEmails />
	</div>
</template>

<script setup lang="ts">
import { defineAsyncComponent, onBeforeMount, ref } from "vue"
import { useRoute } from "vue-router"
import UsersList from "@/components/users/UsersList.vue"

const AllowedEmails = defineAsyncComponent(() => import("@/components/sso/AllowedEmails.vue"))

const route = useRoute()

const highlight = ref<string | undefined>(undefined)

onBeforeMount(() => {
	if (route.query?.user_id) {
		highlight.value = route.query.user_id.toString()
	}
})
</script>
