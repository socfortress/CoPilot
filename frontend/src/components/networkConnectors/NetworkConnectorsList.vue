<template>
	<ServicesList
		v-model:selected="selected"
		type="network-connector"
		:embedded="embedded"
		:hide-totals="hideTotals"
		:selectable="selectable"
		:disabled-ids-list="disabledIdsList"
		:loading="loading"
		:list="list"
	/>
</template>

<script setup lang="ts">
import type { ServiceItemData } from "../services/types"
import { useMessage } from "naive-ui"
import { onBeforeMount, ref } from "vue"
import Api from "@/api"
import ServicesList from "@/components/services/List.vue"

const { embedded, hideTotals, selectable, disabledIdsList } = defineProps<{
	embedded?: boolean
	hideTotals?: boolean
	selectable?: boolean
	disabledIdsList?: (string | number)[]
}>()

const selected = defineModel<ServiceItemData | null>("selected", { default: null })

const message = useMessage()
const loading = ref(false)
const list = ref<ServiceItemData[]>([])

function getAvailableNetworkConnectors() {
	loading.value = true

	Api.networkConnectors
		.getAvailableNetworkConnectors()
		.then(res => {
			if (res.data.success) {
				list.value = (res.data?.network_connector_keys || []).map(obj => ({
					id: obj.id,
					name: obj.network_connector_name,
					description: obj.description,
					details: obj.network_connector_details,
					keys: obj.network_connector_keys
				}))
			} else {
				message.warning(res.data?.message || "An error occurred. Please try again later.")
			}
		})
		.catch(err => {
			message.error(err.response?.data?.message || "An error occurred. Please try again later.")
		})
		.finally(() => {
			loading.value = false
		})
}

onBeforeMount(() => {
	getAvailableNetworkConnectors()
})
</script>
