<template>
	<div>overview: {{ externalId }}</div>
	<pre>{{ techniqueDetails }}</pre>
</template>

<script setup lang="ts">
import type { MitreTechniqueDetails } from "@/types/mitre.d"
import Api from "@/api"
import { useMessage } from "naive-ui"
import { onBeforeMount, ref } from "vue"
import { techniqueResultDetails } from "./mock"

const { externalId } = defineProps<{
	externalId: string
}>()

const message = useMessage()
const loadingDetails = ref(false)
const techniqueDetails = ref<MitreTechniqueDetails | null>(null)

function getDetails() {
	loadingDetails.value = true

	Api.mitre
		.getMitreTechniqueDetails({ external_id: externalId })
		.then(res => {
			if (res.data.success) {
				techniqueDetails.value = res.data.results?.[0] || null
			} else {
				message.warning(res.data?.message || "An error occurred. Please try again later.")
			}
		})
		.catch(err => {
			message.error(err.response?.data?.message || "An error occurred. Please try again later.")
		})
		.finally(() => {
			loadingDetails.value = false
		})
}

onBeforeMount(() => {
	/*
	getDetails()
	*/
	// MOCK
	techniqueDetails.value = techniqueResultDetails
})
</script>
