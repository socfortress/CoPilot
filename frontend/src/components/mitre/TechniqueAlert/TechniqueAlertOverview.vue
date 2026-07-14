<template>
	<n-spin :show="loadingDetails">
		<n-tabs type="line" animated :tabs-padding="fullWidth ? 0 : 24">
			<n-tab-pane name="Overview" tab="Overview" display-directive="show:lazy">
				<div :class="fullWidth ? 'p-0' : 'px-6 pt-3 pb-6'">
					<TechniqueAlertDetails v-if="techniqueDetails" :entity="techniqueDetails" />
				</div>
			</n-tab-pane>
			<n-tab-pane
				name="Groups"
				:tab="`Groups (${techniqueDetails?.groups?.length || 0})`"
				display-directive="show:lazy"
			>
				<div :class="fullWidth ? 'p-0' : 'px-6 pt-3 pb-6'">
					<GroupsList v-if="techniqueDetails" :list="techniqueDetails.groups" />
				</div>
			</n-tab-pane>
			<n-tab-pane
				name="Mitigations"
				:tab="`Mitigations (${techniqueDetails?.mitigations?.length || 0})`"
				display-directive="show:lazy"
			>
				<div :class="fullWidth ? 'p-0' : 'px-6 pt-3 pb-6'">
					<MitigationsList v-if="techniqueDetails" :list="techniqueDetails.mitigations" />
				</div>
			</n-tab-pane>
			<n-tab-pane
				name="Software"
				:tab="`Software (${techniqueDetails?.software?.length || 0})`"
				display-directive="show:lazy"
			>
				<div :class="fullWidth ? 'p-0' : 'px-6 pt-3 pb-6'">
					<SoftwareList v-if="techniqueDetails" :list="techniqueDetails.software" />
				</div>
			</n-tab-pane>
			<n-tab-pane
				name="Tactics"
				:tab="`Tactics (${techniqueDetails?.tactics?.length || 0})`"
				display-directive="show:lazy"
			>
				<div :class="fullWidth ? 'p-0' : 'px-6 pt-3 pb-6'">
					<TacticsList v-if="techniqueDetails" :list="techniqueDetails.tactics" />
				</div>
			</n-tab-pane>
			<n-tab-pane name="Alerts" tab="Alerts" display-directive="show:lazy">
				<div :class="fullWidth ? 'p-0' : 'px-6 pt-3 pb-6'">
					<TechniqueEventsList v-if="techniqueDetails" :external-id />
				</div>
			</n-tab-pane>
			<n-tab-pane name="Atomic test" tab="Atomic test" display-directive="show:lazy">
				<div :class="fullWidth ? 'p-0' : 'px-6 pt-3 pb-6'">
					<TechniqueCardContent :technique-id="externalId" />
				</div>
			</n-tab-pane>
		</n-tabs>
	</n-spin>
</template>

<script setup lang="ts">
import type { MitreTechniqueDetails } from "@/types/mitre"
import { NSpin, NTabPane, NTabs } from "naive-ui"
import Api from "@/api"
import { useEntityDetails } from "@/composables/useEntityDetails"
import TechniqueCardContent from "../AtomicTests/TechniqueCardContent.vue"
import GroupsList from "../Group/GroupsList.vue"
import MitigationsList from "../Mitigation/MitigationsList.vue"
import SoftwareList from "../Software/SoftwareList.vue"
import TacticsList from "../Tactic/TacticsList.vue"
import TechniqueEventsList from "../TechniqueEvents/List.vue"
import TechniqueAlertDetails from "./TechniqueAlertDetails.vue"

const props = defineProps<{
	externalId: string
	fullWidth?: boolean
}>()

const emit = defineEmits<{
	(e: "loaded", value: MitreTechniqueDetails): void
}>()

const { loading: loadingDetails, entity: techniqueDetails } = useEntityDetails<MitreTechniqueDetails, string>({
	entity: () => null,
	id: () => props.externalId,
	fetch: id =>
		Api.wazuh.mitre.getMitreTechniques({ external_id: id }).then(res => ({
			entity: res.data.success ? (res.data.results?.[0] ?? null) : null,
			message: res.data.message
		})),
	notFoundMessage: "An error occurred. Please try again later.",
	errorMessage: "An error occurred. Please try again later.",
	onLoaded: value => emit("loaded", value)
})
</script>
