<template>
	<div>
		<CardEntity embedded hoverable size="small" :loading="loadingDetails">
			<template #headerMain>
				<div class="flex items-center gap-2">
					<span v-if="mitigationDetails" class="text-default">
						{{ mitigationDetails.external_id }}
					</span>
					<span>
						{{ id }}
					</span>
				</div>
			</template>
			<template #headerExtra>
				<EntityDetailsButton
					size="tiny"
					:url="routeAlertsMitreMitigation(id).fullUrl()"
					@view="showDetails = true"
				/>
			</template>
			<template #default>
				<div v-if="mitigationDetails">
					{{ mitigationDetails.name }}
				</div>
				<n-skeleton v-else text class="w-3/4" :height="20" />
			</template>
			<template #footerMain>
				<p v-if="mitigationDetails" class="cursor-text" @click.stop="() => {}">
					<Markdown :source="mitigationDetails.description" />
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
			:title="`Mitigation • ${id}`"
			:bordered="false"
			segmented
		>
			<MitigationOverview :entity="mitigationDetails" />
		</n-modal>
	</div>
</template>

<script setup lang="ts">
import type { ApiError } from "@/types/common"
import type { MitreMitigationDetails } from "@/types/mitre"
import { NModal, NSkeleton, useMessage } from "naive-ui"
import { onBeforeMount, ref } from "vue"
import Api from "@/api"
import CardEntity from "@/components/common/cards/CardEntity.vue"
import EntityDetailsButton from "@/components/common/EntityDetailsButton.vue"
import Markdown from "@/components/common/Markdown.vue"
import { useNavigation } from "@/composables/useNavigation"
import { getApiErrorMessage } from "@/utils"
import MitigationOverview from "./MitigationOverview.vue"

const { id, entity } = defineProps<{
	id: string
	entity?: MitreMitigationDetails
}>()

const emit = defineEmits<{
	(e: "loaded", value: MitreMitigationDetails): void
}>()

const { routeAlertsMitreMitigation } = useNavigation()

const showDetails = ref(false)
const message = useMessage()
const loadingDetails = ref(false)
const mitigationDetails = ref<MitreMitigationDetails | undefined>(undefined)

function getDetails(id: string) {
	loadingDetails.value = true

	Api.wazuh.mitre
		.getMitreMitigations({ id })
		.then(res => {
			if (res.data.success) {
				if (res.data.results?.[0]) {
					mitigationDetails.value = res.data.results[0]
				}
				if (mitigationDetails.value) emit("loaded", mitigationDetails.value)
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
		mitigationDetails.value = entity
	} else if (id) {
		getDetails(id)
	}
})
</script>
