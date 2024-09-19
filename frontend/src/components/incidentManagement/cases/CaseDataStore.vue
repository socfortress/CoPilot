<template>
	<n-spin :show="loading" class="flex flex-col grow min-h-48" content-class="flex flex-col grow ">
		<n-button @click="updateDataStore()">reload</n-button>
		<div class="flex flex-col gap-2">
			<template v-if="dataStore.length">
				<CaseDataStoreItem
					v-for="dataStoreFile of dataStore"
					:key="dataStoreFile.id"
					:data-store-file="dataStoreFile"
					embedded
					@deleted="deleteDataStoreFile(dataStoreFile)"
				/>
			</template>
			<template v-else>
				<n-empty v-if="!loading" description="No items found" class="justify-center h-48" />
			</template>
		</div>
	</n-spin>
</template>

<script setup lang="ts">
import type { CaseDataStore } from "@/types/incidentManagement/cases.d"
import Api from "@/api"
import _clone from "lodash/cloneDeep"
import { NButton, NEmpty, NSpin, useMessage } from "naive-ui"
import { onBeforeMount, ref } from "vue"
import CaseDataStoreItem from "./CaseDataStoreItem.vue"

const { caseId } = defineProps<{
	caseId: number
}>()

const emit = defineEmits<{
	(e: "deleted"): void
	(e: "updated"): void
}>()

const message = useMessage()
const loading = ref(false)
const dataStore = ref<CaseDataStore[]>([])

function deleteDataStoreFile(dataStoreFile: CaseDataStore) {
	dataStore.value = dataStore.value.filter(o => o.id !== dataStoreFile.id)
	emit("deleted")
}

function updateDataStore() {
	emit("updated")
	getCaseDataStore(caseId)
}

function getCaseDataStore(caseId: number) {
	loading.value = true

	Api.incidentManagement
		.getCaseDataStoreFiles(caseId)
		.then(res => {
			if (res.data.success) {
				dataStore.value = res.data?.case_data_store || []
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
	getCaseDataStore(caseId)
})
</script>
