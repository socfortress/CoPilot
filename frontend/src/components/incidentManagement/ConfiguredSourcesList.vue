<template>
	<div class="configured-sources-list">
		<div class="header flex items-center justify-end gap-2 mb-3">
			<div class="info grow flex gap-5">
				<n-popover overlap placement="bottom-start">
					<template #trigger>
						<div class="bg-color border-radius">
							<n-button size="small" class="!cursor-help">
								<template #icon>
									<Icon :name="InfoIcon"></Icon>
								</template>
							</n-button>
						</div>
					</template>
					<div class="flex flex-col gap-2">
						<div class="box">
							Total:
							<code>{{ totalConfiguredSources }}</code>
						</div>
					</div>
				</n-popover>
			</div>
			<div class="actions flex gap-2 items-center">
				<n-button size="small" type="primary" @click="showWizard = true">
					<template #icon>
						<Icon :name="NewSourceConfigurationIcon" :size="15"></Icon>
					</template>
					Create Source Configuration
				</n-button>
			</div>
		</div>
		<n-spin :show="loading" class="min-h-32">
			<div class="list gap-4 grid grid-auto-fill-250" v-if="configuredSourcesList.length">
				<ConfiguredSourceItem
					v-for="source of configuredSourcesList"
					:key="source"
					:source
					class="item-appear item-appear-bottom item-appear-005"
					@deleted="getConfiguredSources()"
				/>
			</div>
			<template v-else>
				<n-empty description="No items found" class="justify-center h-48" v-if="!loading" />
			</template>
		</n-spin>

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
			<SourceConfigurationWizard @submitted="getConfiguredSources()" :disabledSources="configuredSourcesList" />
		</n-modal>
	</div>
</template>
<script setup lang="ts">
import { computed, onBeforeMount, ref, watch } from "vue"
import { NSpin, NEmpty, NPopover, NButton, NModal, useMessage } from "naive-ui"
import Icon from "@/components/common/Icon.vue"
import ConfiguredSourceItem from "./ConfiguredSourceItem.vue"
import SourceConfigurationWizard from "./SourceConfigurationWizard.vue"
import type { SourceName } from "@/types/incidentManagement.d"
import Api from "@/api"

const InfoIcon = "carbon:information"
const NewSourceConfigurationIcon = "carbon:fetch-upload-cloud"
const message = useMessage()
const showWizard = ref(false)
const loading = ref(false)
const configuredSourcesList = ref<SourceName[]>([])
const totalConfiguredSources = computed(() => configuredSourcesList.value.length)
const formCTX = ref<{ reset: () => void } | null>(null)

function getConfiguredSources() {
	loading.value = true

	Api.incidentManagement
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

watch(showWizard, val => {
	if (val) {
		formCTX.value?.reset()
	}
})

onBeforeMount(() => {
	getConfiguredSources()
})
</script>
