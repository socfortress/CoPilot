<template>
	<div class="connectors-list">
		<div class="header mb-4 flex items-center justify-between gap-5">
			<div>
				Total:
				<strong class="font-mono">{{ totalCustomers }}</strong>
			</div>
			<div class="text-secondary text-right">Configure connections to your toolset</div>
		</div>
		<n-spin :show="loadingConnectors">
			<div class="list">
				<template v-if="connectorsList.length">
					<ConnectorItem
						v-for="connector of connectorsList"
						:key="connector.id"
						:connector="connector"
						class="item-appear item-appear-bottom item-appear-005 mb-2"
						@verified="getConnectors()"
						@updated="getConnectors()"
					/>
				</template>
				<template v-else>
					<n-empty v-if="!loadingConnectors" description="No items found" class="h-48 justify-center" />
				</template>
			</div>
		</n-spin>
	</div>
</template>

<script setup lang="ts">
import type { Connector } from "@/types/connectors.d"
import Api from "@/api"
import { NEmpty, NSpin, useMessage } from "naive-ui"
import { computed, onBeforeMount, ref } from "vue"
import ConnectorItem from "./ConnectorItem.vue"

const message = useMessage()
const loadingConnectors = ref(false)
const connectorsList = ref<Connector[]>([])

const totalCustomers = computed<number>(() => {
	return connectorsList.value.length || 0
})

function getConnectors() {
	loadingConnectors.value = true

	Api.connectors
		.getAll()
		.then(res => {
			if (res.data.success) {
				connectorsList.value = res.data?.connectors || []
			} else {
				message.warning(res.data?.message || "An error occurred. Please try again later.")
			}
		})
		.catch(err => {
			message.error(err.response?.data?.message || "An error occurred. Please try again later.")
		})
		.finally(() => {
			loadingConnectors.value = false
		})
}

onBeforeMount(() => {
	getConnectors()
})
</script>

<style lang="scss" scoped>
.connectors-list {
	.list {
		container-type: inline-size;
		min-height: 200px;
	}
}
</style>
