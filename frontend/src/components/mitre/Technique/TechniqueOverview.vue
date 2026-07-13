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
import type { ApiError } from "@/types/common"
import type { MitreTechniqueDetails } from "@/types/mitre"
import { NSpin, NTabPane, NTabs, useMessage } from "naive-ui"
import { computed, onBeforeMount, ref } from "vue"
import Api from "@/api"
import { getApiErrorMessage } from "@/utils"
import GroupsList from "../Group/GroupsList.vue"
import MitigationsList from "../Mitigation/MitigationsList.vue"
import SoftwareList from "../Software/SoftwareList.vue"
import TacticsList from "../Tactic/TacticsList.vue"
import TechniqueAlertDetails from "../TechniqueAlert/TechniqueAlertDetails.vue"
import TechniquesList from "./TechniquesList.vue"

const { entity, id } = defineProps<{
	entity?: MitreTechniqueDetails
	id?: string
	fullWidth?: boolean
}>()

const emit = defineEmits<{
	(e: "loaded", value: MitreTechniqueDetails): void
}>()

const message = useMessage()
const loadingDetails = ref(false)
const fetchedTechnique = ref<MitreTechniqueDetails | undefined>(undefined)

const resolvedEntity = computed(() => entity ?? fetchedTechnique.value)

function getDetails(techniqueId: string) {
	loadingDetails.value = true

	Api.wazuh.mitre
		.getMitreTechniques({ id: techniqueId })
		.then(res => {
			if (res.data.success) {
				if (res.data.results?.[0]) {
					fetchedTechnique.value = res.data.results[0]
					emit("loaded", res.data.results[0])
				}
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
	if (entity) return
	if (id) getDetails(id)
})
</script>
