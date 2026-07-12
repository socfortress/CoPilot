<template>
	<div>
		<CardEntity embedded clickable hoverable size="small" :loading="loadingDetails" @click="showDetails = true">
			<template #headerMain>{{ id }}</template>
			<template #headerExtra>
				<span v-if="groupDetails" class="text-default">
					{{ groupDetails.external_id }}
				</span>
				<n-skeleton v-else text :width="100" :height="18" />
			</template>
			<template #default>
				<div v-if="groupDetails">
					{{ groupDetails.name }}
				</div>
				<n-skeleton v-else text class="w-3/4" :height="20" />
			</template>
			<template #footer>
				<p v-if="groupDetails" class="cursor-text" @click.stop="() => {}">
					<Markdown :source="groupDetails.description" />
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
			:title="`Group • ${id}`"
			:bordered="false"
			segmented
		>
			<GroupOverview :entity="groupDetails" />
		</n-modal>
	</div>
</template>

<script setup lang="ts">
import type { ApiError } from "@/types/common"
import type { MitreGroupDetails } from "@/types/mitre"
import { NModal, NSkeleton, useMessage } from "naive-ui"
import { onBeforeMount, ref } from "vue"
import Api from "@/api"
import CardEntity from "@/components/common/cards/CardEntity.vue"
import Markdown from "@/components/common/Markdown.vue"
import { getApiErrorMessage } from "@/utils"

import GroupOverview from "./GroupOverview.vue"

const { id, entity } = defineProps<{
	id: string
	entity?: MitreGroupDetails
}>()

const emit = defineEmits<{
	(e: "loaded", value: MitreGroupDetails): void
}>()

const showDetails = ref(false)
const message = useMessage()
const loadingDetails = ref(false)
const groupDetails = ref<MitreGroupDetails | undefined>(undefined)

function getDetails(id: string) {
	loadingDetails.value = true

	Api.wazuh.mitre
		.getMitreGroups({ id })
		.then(res => {
			if (res.data.success) {
				if (res.data.results?.[0]) {
					groupDetails.value = res.data.results[0]
				}
				if (groupDetails.value) emit("loaded", groupDetails.value)
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
		groupDetails.value = entity
	} else if (id) {
		getDetails(id)
	}
})
</script>
