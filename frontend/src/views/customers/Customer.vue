<template>
	<div class="page flex flex-col gap-4">
		<n-button quaternary class="self-start" @click="goBack">
			<template #icon>
				<Icon :name="BackIcon" />
			</template>
			Back
		</n-button>

		<CustomerDetails v-if="customerCode" :customer-code @delete="router.push({ name: 'Customers' })" />
		<n-empty v-else description="Invalid customer code" class="h-48 justify-center" />
	</div>
</template>

<script setup lang="ts">
import { NButton, NEmpty } from "naive-ui"
import { computed } from "vue"
import { useRoute, useRouter } from "vue-router"
import Icon from "@/components/common/Icon.vue"
import CustomerDetails from "@/components/customers/CustomerDetails.vue"

const route = useRoute()
const router = useRouter()

const BackIcon = "carbon:arrow-left"

const customerCode = computed(() => {
	const raw = route.params.code
	if (!raw) return null
	return Array.isArray(raw) ? raw[0] : String(raw)
})

function goBack() {
	if (window.history.length > 1) {
		router.back()
		return
	}

	router.push({ name: "Customers" })
}
</script>
