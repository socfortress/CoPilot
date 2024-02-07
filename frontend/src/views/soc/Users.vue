<template>
	<div class="page">
		<SocUsersList :highlight="highlight" />
	</div>
</template>

<script setup lang="ts">
import SocUsersList from "@/components/soc/SocUsers/SocUsersList.vue"
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
