<template>
	<div class="page flex flex-col gap-4">
		<n-button quaternary class="self-start" @click="router.push({ name: 'ExternalServices-NetworkConnectors' })">
			<template #icon>
				<Icon :name="BackIcon" />
			</template>
			Back to network connectors
		</n-button>

		<NetworkConnectorDetails v-if="connectorId != null" :connector-id :embedded="false" />
		<n-empty v-else description="Invalid network connector ID" class="h-48 justify-center" />
	</div>
</template>

<script setup lang="ts">
import { NButton, NEmpty } from "naive-ui"
import { computed } from "vue"
import { useRoute, useRouter } from "vue-router"
import NetworkConnectorDetails from "@/components/networkConnectors/NetworkConnectorDetails.vue"
import Icon from "@/components/common/Icon.vue"

const route = useRoute()
const router = useRouter()

const BackIcon = "carbon:arrow-left"

const connectorId = computed(() => {
	const id = Number(route.params.id)
	return Number.isFinite(id) ? id : null
})
</script>
