<template>
	<n-spin :show="loadingDetails">
		<n-tabs v-if="resolvedEntity" type="line" animated :tabs-padding="fullWidth ? 0 : 24">
			<n-tab-pane name="Overview" tab="Overview" display-directive="show:lazy">
				<div :class="fullWidth ? 'p-0' : 'px-6 pt-3 pb-6'">
					<TechniqueAlertDetails :entity="resolvedEntity" />
				</div>
			</n-tab-pane>
			<n-tab-pane
				name="Tactics"
				:tab="`Tactics (${resolvedEntity.tactics?.length || 0})`"
				display-directive="show:lazy"
			>
				<div :class="fullWidth ? 'p-0' : 'px-6 pt-3 pb-6'">
					<TacticsList :list="resolvedEntity.tactics" />
				</div>
			</n-tab-pane>
			<n-tab-pane
				name="Mitigations"
				:tab="`Mitigations (${resolvedEntity.mitigations?.length || 0})`"
				display-directive="show:lazy"
			>
				<div :class="fullWidth ? 'p-0' : 'px-6 pt-3 pb-6'">
					<MitigationsList :list="resolvedEntity.mitigations" />
				</div>
			</n-tab-pane>
			<n-tab-pane
				v-if="resolvedEntity.techniques?.length"
				name="Techniques"
				:tab="`Techniques (${resolvedEntity.techniques.length})`"
				display-directive="show:lazy"
			>
				<div :class="fullWidth ? 'p-0' : 'px-6 pt-3 pb-6'">
					<TechniquesList :list="resolvedEntity.techniques" />
				</div>
			</n-tab-pane>
			<n-tab-pane
				name="Groups"
				:tab="`Groups (${resolvedEntity.groups?.length || 0})`"
				display-directive="show:lazy"
			>
				<div :class="fullWidth ? 'p-0' : 'px-6 pt-3 pb-6'">
					<GroupsList :list="resolvedEntity.groups" />
				</div>
			</n-tab-pane>
			<n-tab-pane
				name="Software"
				:tab="`Software (${resolvedEntity.software?.length || 0})`"
				display-directive="show:lazy"
			>
				<div :class="fullWidth ? 'p-0' : 'px-6 pt-3 pb-6'">
					<SoftwareList :list="resolvedEntity.software" />
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
import GroupsList from "../Group/GroupsList.vue"
import MitigationsList from "../Mitigation/MitigationsList.vue"
import SoftwareList from "../Software/SoftwareList.vue"
import TacticsList from "../Tactic/TacticsList.vue"
import TechniqueAlertDetails from "../TechniqueAlert/TechniqueAlertDetails.vue"
import TechniquesList from "./TechniquesList.vue"

const props = defineProps<{
	entity?: MitreTechniqueDetails
	id?: string
	fullWidth?: boolean
}>()

const emit = defineEmits<{
	(e: "loaded", value: MitreTechniqueDetails): void
}>()

const { loading: loadingDetails, entity: resolvedEntity } = useEntityDetails<MitreTechniqueDetails, string>({
	entity: () => props.entity,
	id: () => props.id,
	fetch: id =>
		Api.wazuh.mitre.getMitreTechniques({ id }).then(res => ({
			entity: res.data.success ? (res.data.results?.[0] ?? null) : null,
			message: res.data.message
		})),
	notFoundMessage: "An error occurred. Please try again later.",
	errorMessage: "An error occurred. Please try again later.",
	onLoaded: value => emit("loaded", value)
})
</script>
