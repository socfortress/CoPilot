<template>
	<div class="page">
		<SocUsersList :highlight />
	</div>
</template>

<script setup lang="ts">
import { onBeforeMount, ref } from "vue"
import { useRoute } from "vue-router"
import SocUsersList from "@/components/soc/SocUsers/SocUsersList.vue"

const route = useRoute()

const highlight = ref<string | undefined>(undefined)

onBeforeMount(() => {
	if (route.query?.user_id) {
		highlight.value = route.query.user_id.toString()
	}
})
</script>
