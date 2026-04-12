<template>
	<div class="page @container flex flex-col gap-6">
		<AlertDetails v-if="alertId" :alert-id />
	</div>
</template>

<script setup lang="ts">
import { useRoute } from "vue-router"
import AlertDetails from "@/components/alerts/AlertDetails.vue"
import { toNumber } from "@/utils/format"

const route = useRoute()
const alertId = route.params.id ? toNumber(route.params.id as string) : null
</script>
