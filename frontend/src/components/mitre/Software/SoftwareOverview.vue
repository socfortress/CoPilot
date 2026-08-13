<template>
	<n-spin :show="loadingDetails">
		<n-tabs v-if="resolvedEntity" type="line" animated :tabs-padding="fullWidth ? 0 : 24">
			<n-tab-pane name="Overview" tab="Overview" display-directive="show:lazy">
				<div :class="fullWidth ? 'p-0' : 'px-6 pt-3 pb-6'">
					<SoftwareDetails :entity="resolvedEntity" />
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
				name="Techniques"
				:tab="`Techniques (${resolvedEntity.techniques?.length || 0})`"
				display-directive="show:lazy"
			>
				<div :class="fullWidth ? 'p-0' : 'px-6 pt-3 pb-6'">
					<TechniquesList :list="resolvedEntity.techniques" />
				</div>
			</n-tab-pane>
		</n-tabs>
	</n-spin>
</template>

<script setup lang="ts">
import type { MitreSoftwareDetails } from "@/types/mitre"
import { NSpin, NTabPane, NTabs } from "naive-ui"
import Api from "@/api"
import { useEntityDetails } from "@/composables/useEntityDetails"
import GroupsList from "../Group/GroupsList.vue"
import TechniquesList from "../Technique/TechniquesList.vue"
import SoftwareDetails from "./SoftwareDetails.vue"

const props = defineProps<{
	entity?: MitreSoftwareDetails
	id?: string
	fullWidth?: boolean
}>()

const emit = defineEmits<{
	(e: "loaded", value: MitreSoftwareDetails): void
}>()

const { loading: loadingDetails, entity: resolvedEntity } = useEntityDetails<MitreSoftwareDetails, string>({
	entity: () => props.entity,
	id: () => props.id,
	fetch: id =>
		Api.wazuh.mitre.getMitreSoftware({ id }).then(res => ({
			entity: res.data.success ? (res.data.results?.[0] ?? null) : null,
			message: res.data.message
		})),
	notFoundMessage: "An error occurred. Please try again later.",
	errorMessage: "An error occurred. Please try again later.",
	onLoaded: value => emit("loaded", value)
})
</script>
