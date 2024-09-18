<template>
	<ServicesList
		v-model:selected="selected"
		type="integration"
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
import Api from "@/api"
import ServicesList from "@/components/services/List.vue"
import { useMessage } from "naive-ui"
import { onBeforeMount, ref } from "vue"

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

function getAvailableIntegrations() {
	loading.value = true

	Api.integrations
		.getAvailableIntegrations()
		.then(res => {
			if (res.data.success) {
				list.value = (res.data?.available_integrations || []).map(obj => ({
					id: obj.id,
					name: obj.integration_name,
					description: obj.description,
					details: obj.integration_details,
					keys: obj.auth_keys
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
	getAvailableIntegrations()
})
</script>
