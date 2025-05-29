<template>
	<div>
		<CardEntity embedded clickable hoverable size="small" :loading="loadingDetails" @click="showDetails = true">
			<template #headerMain>{{ id }}</template>
			<template #headerExtra>
				<span v-if="techniqueDetails" class="text-default">
					{{ techniqueDetails.external_id }}
				</span>
				<n-skeleton v-else text :width="100" :height="18" />
			</template>
			<template #default>
				<div v-if="techniqueDetails">
					{{ techniqueDetails.name }}
				</div>
				<n-skeleton v-else text style="width: 60%" :height="20" />
			</template>
			<template #footer>
				<p v-if="techniqueDetails" class="cursor-text" @click.stop="() => {}">
					<Suspense>
						<Markdown :source="techniqueDetails.description" />
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
			:title="`Technique • ${id}`"
			:bordered="false"
			segmented
		>
			<n-tabs type="line" animated :tabs-padding="24">
				<n-tab-pane name="Overview" tab="Overview" display-directive="show:lazy">
					<div class="px-7 pb-7 pt-4">
						<TechniqueAlertDetails :entity="techniqueDetails" />
					</div>
				</n-tab-pane>
				<n-tab-pane
					name="Tactics"
					:tab="`Tactics (${techniqueDetails?.tactics?.length || 0})`"
					display-directive="show:lazy"
				>
					<div class="px-7 pb-7 pt-4">
						<TacticsList v-if="techniqueDetails" :list="techniqueDetails.tactics" />
					</div>
				</n-tab-pane>
				<n-tab-pane
					name="Mitigations"
					:tab="`Mitigations (${techniqueDetails?.mitigations?.length || 0})`"
					display-directive="show:lazy"
				>
					<div class="px-7 pb-7 pt-4">
						<MitigationsList v-if="techniqueDetails" :list="techniqueDetails.mitigations" />
					</div>
				</n-tab-pane>
				<n-tab-pane
					v-if="techniqueDetails?.techniques?.length"
					name="Techniques"
					:tab="`Techniques (${techniqueDetails?.techniques?.length || 0})`"
					display-directive="show:lazy"
				>
					<div class="px-7 pb-7 pt-4">
						<TechniquesList :list="techniqueDetails.techniques" />
					</div>
				</n-tab-pane>
				<n-tab-pane
					name="Groups"
					:tab="`Groups (${techniqueDetails?.groups?.length || 0})`"
					display-directive="show:lazy"
				>
					<div class="px-7 pb-7 pt-4">
						<GroupsList v-if="techniqueDetails" :list="techniqueDetails.groups" />
					</div>
				</n-tab-pane>
				<n-tab-pane
					name="Software"
					:tab="`Software (${techniqueDetails?.software?.length || 0})`"
					display-directive="show:lazy"
				>
					<div class="px-7 pb-7 pt-4">
						<SoftwareList v-if="techniqueDetails" :list="techniqueDetails.software" />
					</div>
				</n-tab-pane>
			</n-tabs>
		</n-modal>
	</div>
</template>

<script setup lang="ts">
import type { MitreTechniqueDetails } from "@/types/mitre.d"
import { NModal, NSkeleton, NTabPane, NTabs, useMessage } from "naive-ui"
import { defineAsyncComponent, onBeforeMount, ref } from "vue"
import Api from "@/api"
import CardEntity from "@/components/common/cards/CardEntity.vue"
import GroupsList from "../Group/GroupsList.vue"
import MitigationsList from "../Mitigation/MitigationsList.vue"
import SoftwareList from "../Software/SoftwareList.vue"
import TacticsList from "../Tactic/TacticsList.vue"
import TechniqueAlertDetails from "../TechniqueAlert/TechniqueAlertDetails.vue"
import TechniquesList from "./TechniquesList.vue"

const { id, entity } = defineProps<{
	id: string
	entity?: MitreTechniqueDetails
}>()

const emit = defineEmits<{
	(e: "loaded", value: MitreTechniqueDetails): void
}>()

const Markdown = defineAsyncComponent(() => import("@/components/common/Markdown.vue"))

const showDetails = ref(false)
const message = useMessage()
const loadingDetails = ref(false)
const techniqueDetails = ref<MitreTechniqueDetails | undefined>(undefined)

function getDetails(id: string) {
	loadingDetails.value = true

	Api.mitre
		.getMitreTechniques({ id })
		.then(res => {
			if (res.data.success) {
				techniqueDetails.value = res.data.results?.[0] || null
				if (techniqueDetails.value) emit("loaded", techniqueDetails.value)
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
		techniqueDetails.value = entity
	} else if (id) {
		getDetails(id)
	}
})
</script>
