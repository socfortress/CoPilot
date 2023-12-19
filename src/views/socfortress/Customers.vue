<template>
	<div class="page">
		<CustomersList :highlight="highlight" />
	</div>
</template>

<script setup lang="ts">
import CustomersList from "@/components/customers/CustomersList.vue"
import { onBeforeMount, ref } from "vue"
import { useRoute } from "vue-router"

const route = useRoute()

const highlight = ref<string | undefined>(undefined)

onBeforeMount(() => {
	if (route.query?.code) {
		highlight.value = route.query.code.toString()
	}
})
</script>
