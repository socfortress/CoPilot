<template>
	<div>
		<CardEntity embedded clickable hoverable size="small" :loading="loadingDetails" @click="showDetails = true">
			<template #headerMain>{{ id }}</template>
			<template #headerExtra>
				<span v-if="mitigationDetails" class="text-default">
					{{ mitigationDetails.external_id }}
				</span>
				<n-skeleton v-else text :width="100" :height="18" />
			</template>
			<template #default>
				<div v-if="mitigationDetails">
					{{ mitigationDetails.name }}
				</div>
				<n-skeleton v-else text style="width: 60%" :height="20" />
			</template>
			<template #footer>
				<p v-if="mitigationDetails" class="cursor-text" @click.stop="() => {}">
					<Markdown :source="mitigationDetails.description" />
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
			content-class="p-0!"
			:style="{ maxWidth: 'min(900px, 90vw)', minHeight: 'min(600px, 90vh)', overflow: 'hidden' }"
			:title="`Mitigation • ${id}`"
			:bordered="false"
			segmented
		>
			<n-tabs type="line" animated :tabs-padding="24">
				<n-tab-pane name="Overview" tab="Overview" display-directive="show:lazy">
					<div class="px-7 pt-4 pb-7">
						<MitigationDetails :entity="mitigationDetails" />
					</div>
				</n-tab-pane>
				<n-tab-pane
					name="Techniques"
					:tab="`Techniques (${mitigationDetails?.techniques?.length || 0})`"
					display-directive="show:lazy"
				>
					<div class="px-7 pt-4 pb-7">
						<TechniquesList v-if="mitigationDetails" :list="mitigationDetails.techniques" />
					</div>
				</n-tab-pane>
			</n-tabs>
		</n-modal>
	</div>
</template>

<script setup lang="ts">
import type { MitreMitigationDetails } from "@/types/mitre.d"
import { NModal, NSkeleton, NTabPane, NTabs, useMessage } from "naive-ui"
import { defineAsyncComponent, onBeforeMount, ref } from "vue"
import Api from "@/api"
import CardEntity from "@/components/common/cards/CardEntity.vue"
import TechniquesList from "../Technique/TechniquesList.vue"
import MitigationDetails from "./MitigationDetails.vue"

const { id, entity } = defineProps<{
	id: string
	entity?: MitreMitigationDetails
}>()

const emit = defineEmits<{
	(e: "loaded", value: MitreMitigationDetails): void
}>()

const Markdown = defineAsyncComponent(() => import("@/components/common/Markdown.vue"))

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
				mitigationDetails.value = res.data.results?.[0] || null
				if (mitigationDetails.value) emit("loaded", mitigationDetails.value)
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
		mitigationDetails.value = entity
	} else if (id) {
		getDetails(id)
	}
})
</script>
