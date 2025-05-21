<template>
	<n-spin :show="loadingDetails">
		<n-tabs type="line" animated :tabs-padding="24">
			<n-tab-pane name="Overview" tab="Overview" display-directive="show:lazy">
				<div class="px-7 pb-7 pt-4">
					<TechniqueDetails v-if="techniqueDetails" :entity="techniqueDetails" />
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
				name="Mitigations"
				:tab="`Mitigations (${techniqueDetails?.mitigations?.length || 0})`"
				display-directive="show:lazy"
			>
				<div class="px-7 pb-7 pt-4">
					<MitigationsList v-if="techniqueDetails" :list="techniqueDetails.mitigations" />
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
			<n-tab-pane
				name="Tactics"
				:tab="`Tactics (${techniqueDetails?.tactics?.length || 0})`"
				display-directive="show:lazy"
			>
				<div class="px-7 pb-7 pt-4">
					<TacticsList v-if="techniqueDetails" :list="techniqueDetails.tactics" />
				</div>
			</n-tab-pane>
		</n-tabs>
	</n-spin>
</template>

<script setup lang="ts">
import type { MitreTechniqueDetails } from "@/types/mitre.d"
import { NSpin, NTabPane, NTabs, useMessage } from "naive-ui"
import { onBeforeMount, ref } from "vue"
import Api from "@/api"
import GroupsList from "../Group/GroupsList.vue"
import MitigationsList from "../Mitigation/MitigationsList.vue"
import { techniqueResultDetails } from "../mock"
import SoftwareList from "../Software/SoftwareList.vue"
import TacticsList from "../Tactic/TacticsList.vue"
import TechniqueDetails from "./TechniqueDetails.vue"

const { externalId } = defineProps<{
	externalId: string
}>()

const message = useMessage()
const loadingDetails = ref(false)
const techniqueDetails = ref<MitreTechniqueDetails | undefined>(undefined)

function getDetails(id: string) {
	loadingDetails.value = true

	Api.mitre
		.getMitreTechniqueDetails({ external_id: id })
		.then(res => {
			if (res.data.success) {
				techniqueDetails.value = res.data.results?.[0] || null
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
	/*
	getDetails(externalId)
	 */
	// MOCK
	techniqueDetails.value = techniqueResultDetails
})
</script>
