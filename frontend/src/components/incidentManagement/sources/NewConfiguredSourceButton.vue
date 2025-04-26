<template>
	<div>
		<n-button size="small" type="primary" @click="showWizard = true">
			<template #icon>
				<Icon :name="NewSourceConfigurationIcon" :size="15"></Icon>
			</template>
			Create Source Configuration
		</n-button>

		<n-modal
			v-model:show="showWizard"
			display-directive="show"
			preset="card"
			:style="{ maxWidth: 'min(600px, 90vw)', minHeight: 'min(200px, 90vh)', overflow: 'hidden' }"
			title="Create Source Configuration"
			:bordered="false"
			content-class="flex flex-col !p-0"
			segmented
		>
			<SourceConfigurationWizard :disabled-sources="configuredSourcesList" @submitted="submitted()" />
		</n-modal>
	</div>
</template>

<script setup lang="ts">
import type { SourceName } from "@/types/incidentManagement/sources.d"
import Api from "@/api"
import Icon from "@/components/common/Icon.vue"
import { NButton, NModal, useMessage } from "naive-ui"
import { onBeforeMount, ref, watch } from "vue"
import SourceConfigurationWizard from "./SourceConfigurationWizard.vue"

const { disabledSources } = defineProps<{ disabledSources?: SourceName[] }>()

const emit = defineEmits<{
	(e: "success"): void
}>()

const NewSourceConfigurationIcon = "carbon:fetch-upload-cloud"
const message = useMessage()
const showWizard = ref(false)
const loading = ref(false)
const configuredSourcesList = ref<SourceName[]>([])
const formCTX = ref<{ reset: () => void } | null>(null)

function getConfiguredSources() {
	loading.value = true

	Api.incidentManagement.sources
		.getConfiguredSources()
		.then(res => {
			if (res.data.success) {
				configuredSourcesList.value = res.data?.sources || []
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

function submitted() {
	getConfiguredSources()
	emit("success")
}

watch(showWizard, val => {
	if (val) {
		formCTX.value?.reset()
	}
})

onBeforeMount(() => {
	if (disabledSources?.length) {
		configuredSourcesList.value = disabledSources
	} else {
		getConfiguredSources()
	}
})
</script>
