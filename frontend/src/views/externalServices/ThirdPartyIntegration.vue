<template>
	<div class="page flex flex-col gap-4">
		<n-button
			quaternary
			class="self-start"
			@click="router.push({ name: 'ExternalServices-ThirdPartyIntegrations' })"
		>
			<template #icon>
				<Icon :name="BackIcon" />
			</template>
			Back to integrations
		</n-button>

		<IntegrationDetails v-if="integrationId != null" :integration-id :embedded="false" />
		<n-empty v-else description="Invalid integration ID" class="h-48 justify-center" />
	</div>
</template>

<script setup lang="ts">
import { NButton, NEmpty } from "naive-ui"
import { computed } from "vue"
import { useRoute, useRouter } from "vue-router"
import Icon from "@/components/common/Icon.vue"
import IntegrationDetails from "@/components/integrations/IntegrationDetails.vue"

const route = useRoute()
const router = useRouter()

const BackIcon = "carbon:arrow-left"

const integrationId = computed(() => {
	const id = Number(route.params.id)
	return Number.isFinite(id) ? id : null
})
</script>
