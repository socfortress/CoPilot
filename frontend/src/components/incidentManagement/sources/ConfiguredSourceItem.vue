<template>
	<div>
		<CardEntity hoverable embedded>
			<template #headerMain>
				<span class="text-default font-semibold">{{ source }}</span>
			</template>
			<template #headerExtra>
				<EntityDetailsButton size="tiny" :route="routeIncidentManagementSource(source)" @view="openDetails()" />
			</template>

			<template v-if="sourceConfiguration || loadingConfig" #mainExtra>
				<n-spin :show="loadingConfig" class="min-h-5">
					<div v-if="sourceConfiguration" class="flex flex-wrap items-center gap-1.5">
						<Badge type="splitted" color="primary">
							<template #label>Fields</template>
							<template #value>{{ sourceConfiguration.field_names.length }}</template>
						</Badge>

						<Badge v-if="sourceConfiguration.ioc_field_names?.length" type="splitted" color="warning">
							<template #label>IOC</template>
							<template #value>{{ sourceConfiguration.ioc_field_names.length }}</template>
						</Badge>

						<Badge v-if="sourceConfiguration.asset_name" type="splitted">
							<template #label>Asset</template>
							<template #value>
								<span class="font-mono">{{ sourceConfiguration.asset_name }}</span>
							</template>
						</Badge>

						<Badge v-if="sourceConfiguration.timefield_name" type="splitted">
							<template #label>Time</template>
							<template #value>
								<span class="font-mono">{{ sourceConfiguration.timefield_name }}</span>
							</template>
						</Badge>
					</div>
				</n-spin>
			</template>
		</CardEntity>

		<n-modal
			v-model:show="showDetails"
			:style="{ maxWidth: 'min(700px, 90vw)', minHeight: 'min(320px, 90vh)', overflow: 'hidden' }"
			display-directive="show"
		>
			<n-card
				content-class="flex flex-col"
				:title="source"
				closable
				:bordered="false"
				segmented
				role="modal"
				@close="closeDetails()"
			>
				<SourceConfigurationDetails deletable :source @deleted="handleDeleted()" />
			</n-card>
		</n-modal>
	</div>
</template>

<script setup lang="ts">
import type { ApiError } from "@/types/common"
import type { SourceConfiguration, SourceName } from "@/types/incidentManagement/sources"
import { NCard, NModal, NSpin, useMessage } from "naive-ui"
import { onBeforeMount, ref } from "vue"
import Api from "@/api"
import Badge from "@/components/common/Badge.vue"
import CardEntity from "@/components/common/cards/CardEntity.vue"
import EntityDetailsButton from "@/components/common/EntityDetailsButton.vue"
import { useNavigation } from "@/composables/useNavigation"
import { getApiErrorMessage } from "@/utils"
import SourceConfigurationDetails from "./SourceConfigurationDetails.vue"

const { source } = defineProps<{ source: SourceName }>()

const emit = defineEmits<{
	(e: "deleted"): void
}>()

const message = useMessage()
const { routeIncidentManagementSource } = useNavigation()
const loadingConfig = ref(false)
const showDetails = ref(false)
const sourceConfiguration = ref<SourceConfiguration | null>(null)

function getSourceConfiguration() {
	loadingConfig.value = true

	Api.incidentManagement.sources
		.getSourceConfiguration(source)
		.then(res => {
			if (res.data.success) {
				sourceConfiguration.value = {
					field_names: res.data.field_names || [],
					ioc_field_names: res.data.ioc_field_names || [],
					asset_name: res.data.asset_name || "",
					timefield_name: res.data.timefield_name || "",
					alert_title_name: res.data.alert_title_name || "",
					source: res.data.source || source
				}
			}
		})
		.catch(err => {
			message.error(getApiErrorMessage(err as ApiError) || "An error occurred. Please try again later.")
		})
		.finally(() => {
			loadingConfig.value = false
		})
}

function openDetails() {
	showDetails.value = true
}

function closeDetails() {
	showDetails.value = false
}

function handleDeleted() {
	showDetails.value = false
	emit("deleted")
}

onBeforeMount(() => {
	getSourceConfiguration()
})
</script>
