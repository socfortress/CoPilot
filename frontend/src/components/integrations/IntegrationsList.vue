<template>
	<ServicesList
		type="integration"
		:embedded="embedded"
		:hideTotals="hideTotals"
		:selectable="selectable"
		:disabledIdsList="disabledIdsList"
		:loading="loading"
		:list="list"
		v-model:selected="selected"
	/>
</template>

<script setup lang="ts">
import { ref, onBeforeMount } from "vue"
import { useMessage } from "naive-ui"
import Api from "@/api"
import ServicesList from "@/components/services/List.vue"
import type { ServiceItemData } from "../services/types"

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
