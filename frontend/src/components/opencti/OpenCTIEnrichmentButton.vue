<template>
	<div v-if="available">
		<n-button :size="size || 'small'" ghost type="primary" :loading @click="lookup()">
			<template #icon>
				<Icon :name="OpenCTIIcon" />
			</template>
			Enrich with OpenCTI
		</n-button>

		<n-modal
			v-model:show="showModal"
			preset="card"
			:style="{ maxWidth: 'min(640px, 90vw)' }"
			:bordered="false"
			segmented
			title="OpenCTI Enrichment"
		>
			<OpenCTILookupResult v-if="response" :lookup="response" />
		</n-modal>
	</div>
</template>

<script setup lang="ts">
import type { ButtonSize } from "naive-ui"
import type { ApiError } from "@/types/common"
import type { OpenCTIObservableLookup } from "@/types/opencti"
import { NButton, NModal, useMessage } from "naive-ui"
import { ref } from "vue"
import Api from "@/api"
import Icon from "@/components/common/Icon.vue"
import { useOpenCTIAvailability } from "@/composables/useOpenCTIAvailability"
import { getApiErrorMessage } from "@/utils"
import OpenCTILookupResult from "./OpenCTILookupResult.vue"

const { iocValue, size } = defineProps<{
	iocValue: string
	size?: ButtonSize
}>()

const OpenCTIIcon = "mdi:shield-search"
const message = useMessage()
const { available } = useOpenCTIAvailability()
const showModal = ref(false)
const loading = ref(false)
const response = ref<OpenCTIObservableLookup | null>(null)

function lookup() {
	loading.value = true

	Api.opencti
		.lookupObservable(iocValue)
		.then(res => {
			response.value = res.data
			showModal.value = true
		})
		.catch(err => {
			message.error(getApiErrorMessage(err as ApiError) || "An error occurred. Please try again later.")
		})
		.finally(() => {
			loading.value = false
		})
}
</script>
