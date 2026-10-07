<template>
	<div class="page">
		<UbaDetailPage v-if="customerCode && id" :id :customer-code kind="entity" />
		<n-empty v-else description="Invalid UBA entity" class="h-48 justify-center" />
	</div>
</template>

<script setup lang="ts">
import { NEmpty } from "naive-ui"
import UbaDetailPage from "@/components/uba/UbaDetailPage.vue"
import { useRouteParam } from "@/composables/useNavigation"

const customerCode = useRouteParam("customerCode")
const id = useRouteParam("entityKey")
</script>
