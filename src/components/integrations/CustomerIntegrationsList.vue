<template>
	<div class="integrations-list">
		<div class="header mb-4 flex gap-2 justify-between items-center">
			<div>
				Total:
				<strong class="font-mono">{{ totalIntegrations }}</strong>
			</div>
		</div>
		<n-spin :show="loadingIntegrations">
			<div class="list">
				<template v-if="integrationsList.length">
					<IntegrationItem
						v-for="integration of integrationsList"
						:key="integration.id"
						:integration="integration"
						:embedded="embedded"
						class="item-appear item-appear-bottom item-appear-005 mb-2"
					/>
				</template>
				<template v-else>
					<n-empty description="No items found" class="justify-center h-48" v-if="!loadingIntegrations" />
				</template>
			</div>
		</n-spin>
	</div>
</template>

<script setup lang="ts">
import { ref, onBeforeMount, computed } from "vue"
import { useMessage, NSpin, NEmpty } from "naive-ui"
import Api from "@/api"
import IntegrationItem from "./IntegrationItem.vue"
import type { AvailableIntegration } from "@/types/integrations"

const { customerCode } = defineProps<{
	embedded?: boolean
	customerCode: string
}>()

const message = useMessage()
const loadingIntegrations = ref(false)
const integrationsList = ref<AvailableIntegration[]>([])

const totalIntegrations = computed<number>(() => {
	return integrationsList.value.length || 0
})

function getAvailableIntegrations() {
	loadingIntegrations.value = true

	Api.integrations
		.getAvailableIntegrations()
		.then(res => {
			if (res.data.success) {
				integrationsList.value = res.data?.available_integrations || []
			} else {
				message.warning(res.data?.message || "An error occurred. Please try again later.")
			}
		})
		.catch(err => {
			message.error(err.response?.data?.message || "An error occurred. Please try again later.")
		})
		.finally(() => {
			loadingIntegrations.value = false
		})
}

onBeforeMount(() => {
	getAvailableIntegrations()
})
</script>

<style lang="scss" scoped>
.integrations-list {
	.list {
		container-type: inline-size;
		min-height: 200px;
	}
}
</style>
