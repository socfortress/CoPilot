<template>
	<div class="connectors-list">
		<div class="header mb-4 flex gap-5 justify-between items-center">
			<div>
				Total:
				<strong class="font-mono">{{ totalCustomers }}</strong>
			</div>
			<div class="text-secondary-color text-right">Configure connections to your toolset</div>
		</div>
		<n-spin :show="loadingConnectors">
			<div class="list">
				<template v-if="connectorsList.length">
					<ConnectorItem
						v-for="connector of connectorsList"
						:key="connector.id"
						:connector="connector"
						@verified="getConnectors()"
						@updated="getConnectors()"
						class="item-appear item-appear-bottom item-appear-005 mb-2"
					/>
				</template>
				<template v-else>
					<n-empty description="No items found" class="justify-center h-48" v-if="!loadingConnectors" />
				</template>
			</div>
		</n-spin>
	</div>
</template>

<script setup lang="ts">
import { ref, onBeforeMount, computed } from "vue"
import { useMessage, NSpin, NEmpty } from "naive-ui"
import Api from "@/api"
import ConnectorItem from "./ConnectorItem.vue"
import type { Connector } from "@/types/connectors.d"

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
