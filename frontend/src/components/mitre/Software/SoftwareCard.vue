<template>
	<div>
		<CardEntity embedded clickable hoverable size="small" :loading="loadingDetails" @click="showDetails = true">
			<template #headerMain>{{ id }}</template>
			<template #headerExtra>
				<span v-if="softwareDetails" class="text-default">
					{{ softwareDetails.external_id }}
				</span>
				<n-skeleton v-else text :width="100" :height="18" />
			</template>
			<template #default>
				<div v-if="softwareDetails">
					{{ softwareDetails.name }}
				</div>
				<n-skeleton v-else text style="width: 60%" :height="20" />
			</template>
			<template #footer>
				<p v-if="softwareDetails" @click.stop="() => {}">
					<Suspense>
						<Markdown :source="softwareDetails.description" />
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
			:title="`Software • ${id}`"
			:bordered="false"
			segmented
		>
			<n-tabs type="line" animated :tabs-padding="24">
				<n-tab-pane name="Overview" tab="Overview" display-directive="show:lazy">
					<div class="px-7 pb-7 pt-4">
						<SoftwareDetails :entity="softwareDetails" />
					</div>
				</n-tab-pane>
				<n-tab-pane
					name="Groups"
					:tab="`Groups (${softwareDetails?.groups?.length || 0})`"
					display-directive="show:lazy"
				>
					<div class="px-7 pb-7 pt-4">
						<GroupsList v-if="softwareDetails" :list="softwareDetails.groups" />
					</div>
				</n-tab-pane>
				<n-tab-pane
					name="Techniques"
					:tab="`Techniques (${softwareDetails?.techniques?.length || 0})`"
					display-directive="show:lazy"
				>
					<div class="px-7 pb-7 pt-4">
						<TechniquesList v-if="softwareDetails" :list="softwareDetails.techniques" />
					</div>
				</n-tab-pane>
			</n-tabs>
		</n-modal>
	</div>
</template>

<script setup lang="ts">
import type { MitreSoftwareDetails } from "@/types/mitre.d"
import { NModal, NSkeleton, NTabPane, NTabs, useMessage } from "naive-ui"
import { defineAsyncComponent, onBeforeMount, ref } from "vue"
import Api from "@/api"
import CardEntity from "@/components/common/cards/CardEntity.vue"
import GroupsList from "../Group/GroupsList.vue"
import TechniquesList from "../Technique/TechniquesList.vue"
import SoftwareDetails from "./SoftwareDetails.vue"

const { id, entity } = defineProps<{
	id: string
	entity?: MitreSoftwareDetails
}>()

const emit = defineEmits<{
	(e: "loaded", value: MitreSoftwareDetails): void
}>()

const Markdown = defineAsyncComponent(() => import("@/components/common/Markdown.vue"))

const showDetails = ref(false)
const message = useMessage()
const loadingDetails = ref(false)
const softwareDetails = ref<MitreSoftwareDetails | undefined>(undefined)

function getDetails(id: string) {
	loadingDetails.value = true

	Api.mitre
		.getMitreSoftware({ id })
		.then(res => {
			if (res.data.success) {
				softwareDetails.value = res.data.results?.[0] || null
				if (softwareDetails.value) emit("loaded", softwareDetails.value)
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
		softwareDetails.value = entity
	} else if (id) {
		getDetails(id)
	}
})
</script>
