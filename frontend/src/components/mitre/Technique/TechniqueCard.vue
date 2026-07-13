<template>
	<div>
		<CardEntity embedded hoverable size="small" :loading="loadingDetails">
			<template #headerMain>
				<div class="flex items-center gap-2">
					<span v-if="techniqueDetails" class="text-default">
						{{ techniqueDetails.external_id }}
					</span>
					<span>
						{{ id }}
					</span>
				</div>
			</template>
			<template #headerExtra>
				<EntityDetailsButton
					size="tiny"
					:url="routeAlertsMitreTechniques(id).fullUrl()"
					@view="showDetails = true"
				/>
			</template>
			<template #default>
				<div v-if="techniqueDetails">
					{{ techniqueDetails.name }}
				</div>
				<n-skeleton v-else text class="w-3/4" :height="20" />
			</template>
			<template #footerMain>
				<p v-if="techniqueDetails" class="cursor-text" @click.stop="() => {}">
					<Markdown :source="techniqueDetails.description" />
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
			:title="`Technique • ${id}`"
			:bordered="false"
			segmented
		>
			<TechniqueOverview :entity="techniqueDetails" />
		</n-modal>
	</div>
</template>

<script setup lang="ts">
import type { ApiError } from "@/types/common"
import type { MitreTechniqueDetails } from "@/types/mitre"
import { NModal, NSkeleton, useMessage } from "naive-ui"
import { onBeforeMount, ref } from "vue"
import Api from "@/api"
import CardEntity from "@/components/common/cards/CardEntity.vue"
import EntityDetailsButton from "@/components/common/EntityDetailsButton.vue"
import Markdown from "@/components/common/Markdown.vue"
import { useNavigation } from "@/composables/useNavigation"
import { getApiErrorMessage } from "@/utils"
import TechniqueOverview from "./TechniqueOverview.vue"

const { id, entity } = defineProps<{
	id: string
	entity?: MitreTechniqueDetails
}>()

const emit = defineEmits<{
	(e: "loaded", value: MitreTechniqueDetails): void
}>()

const { routeAlertsMitreTechniques } = useNavigation()

const showDetails = ref(false)
const message = useMessage()
const loadingDetails = ref(false)
const techniqueDetails = ref<MitreTechniqueDetails | undefined>(undefined)

function getDetails(id: string) {
	loadingDetails.value = true

	Api.wazuh.mitre
		.getMitreTechniques({ id })
		.then(res => {
			if (res.data.success) {
				if (res.data.results?.[0]) {
					techniqueDetails.value = res.data.results[0]
				}
				if (techniqueDetails.value) emit("loaded", techniqueDetails.value)
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
		techniqueDetails.value = entity
	} else if (id) {
		getDetails(id)
	}
})
</script>
