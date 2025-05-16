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
				<n-skeleton v-else text style="width: 60%" :height="20" />
			</template>
			<template #footer>
				<p v-if="groupDetails" @click.stop="() => {}">
					<Suspense>
						<Markdown :source="groupDetails.description" />
					</Suspense>
				</p>
				<div v-else>
					<n-skeleton text :repeat="2" :height="16" />
					<n-skeleton text style="width: 40%" :height="16" />
				</div>
			</template>
		</CardEntity>
		<n-modal
			v-model:show="showDetails"
			display-directive="show"
			preset="card"
			content-class="!p-0"
			:style="{ maxWidth: 'min(900px, 90vw)', minHeight: 'min(600px, 90vh)', overflow: 'hidden' }"
			:title="`${id}`"
			:bordered="false"
			segmented
		>
			{{ id }}
		</n-modal>
	</div>
</template>

<script setup lang="ts">
import type { MitreGroupDetails } from "@/types/mitre.d"
import { NModal, NSkeleton, useMessage } from "naive-ui"
import { defineAsyncComponent, onBeforeMount, ref } from "vue"
import Api from "@/api"
import CardEntity from "@/components/common/cards/CardEntity.vue"

const { id, entity } = defineProps<{
	id: string
	entity?: MitreGroupDetails
}>()

const emit = defineEmits<{
	(e: "loaded", value: MitreGroupDetails): void
}>()

const Markdown = defineAsyncComponent(() => import("@/components/common/Markdown.vue"))

const showDetails = ref(false)
const message = useMessage()
const loadingDetails = ref(false)
const groupDetails = ref<MitreGroupDetails | undefined>(undefined)

function getDetails(id: string) {
	loadingDetails.value = true

	Api.mitre
		.getMitreGroups({ id })
		.then(res => {
			if (res.data.success) {
				groupDetails.value = res.data.results?.[0] || null
				emit("loaded", groupDetails.value)
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
	if (entity) {
		groupDetails.value = entity
	} else if (id) {
		getDetails(id)
	}
})
</script>
