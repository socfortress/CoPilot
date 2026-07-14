<template>
	<div>
		<CardEntity embedded hoverable size="small" :loading="loadingDetails">
			<template #headerMain>
				<div class="flex items-center gap-2">
					<span v-if="softwareDetails" class="text-default">
						{{ softwareDetails.external_id }}
					</span>
					<span>
						{{ id }}
					</span>
				</div>
			</template>
			<template #headerExtra>
				<EntityDetailsButton size="tiny" :route="routeAlertsMitreSoftware(id)" @view="showDetails = true" />
			</template>
			<template #default>
				<div v-if="softwareDetails">
					{{ softwareDetails.name }}
				</div>
				<n-skeleton v-else text class="w-3/4" :height="20" />
			</template>
			<template #footerMain>
				<p v-if="softwareDetails" class="cursor-text" @click.stop="() => {}">
					<Markdown :source="softwareDetails.description" />
				</p>
				<div v-else>
					<n-skeleton text :repeat="2" :height="16" />
					<n-skeleton text class="w-2/4" :height="16" />
				</div>
			</template>
		</CardEntity>
		<n-modal
			v-model:show="showDetails"
			display-directive="show"
			preset="card"
			content-class="p-0!"
			:style="{ maxWidth: 'min(900px, 90vw)', minHeight: 'min(600px, 90vh)', overflow: 'hidden' }"
			:title="`Software • ${id}`"
			:bordered="false"
			segmented
		>
			<SoftwareOverview :entity="softwareDetails" />
		</n-modal>
	</div>
</template>

<script setup lang="ts">
import type { ApiError } from "@/types/common"
import type { MitreSoftwareDetails } from "@/types/mitre"
import { NModal, NSkeleton, useMessage } from "naive-ui"
import { onBeforeMount, ref } from "vue"
import Api from "@/api"
import CardEntity from "@/components/common/cards/CardEntity.vue"
import EntityDetailsButton from "@/components/common/EntityDetailsButton.vue"
import Markdown from "@/components/common/Markdown.vue"
import { useNavigation } from "@/composables/useNavigation"
import { getApiErrorMessage } from "@/utils"

import SoftwareOverview from "./SoftwareOverview.vue"

const { id, entity } = defineProps<{
	id: string
	entity?: MitreSoftwareDetails
}>()

const emit = defineEmits<{
	(e: "loaded", value: MitreSoftwareDetails): void
}>()

const { routeAlertsMitreSoftware } = useNavigation()

const showDetails = ref(false)
const message = useMessage()
const loadingDetails = ref(false)
const softwareDetails = ref<MitreSoftwareDetails | undefined>(undefined)

function getDetails(id: string) {
	loadingDetails.value = true

	Api.wazuh.mitre
		.getMitreSoftware({ id })
		.then(res => {
			if (res.data.success) {
				if (res.data.results?.[0]) {
					softwareDetails.value = res.data.results[0]
				}
				if (softwareDetails.value) emit("loaded", softwareDetails.value)
			} else {
				message.warning(res.data?.message || "An error occurred. Please try again later.")
			}
		})
		.catch(err => {
			message.error(getApiErrorMessage(err as ApiError) || "An error occurred. Please try again later.")
		})
		.finally(() => {
			loadingDetails.value = false
		})
}

onBeforeMount(() => {
	if (entity) {
		softwareDetails.value = entity
	} else if (id) {
		getDetails(id)
	}
})
</script>
