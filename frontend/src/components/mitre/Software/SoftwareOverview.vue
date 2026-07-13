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
import type { ApiError } from "@/types/common"
import type { MitreSoftwareDetails } from "@/types/mitre"
import { NSpin, NTabPane, NTabs, useMessage } from "naive-ui"
import { computed, onBeforeMount, ref } from "vue"
import Api from "@/api"
import { getApiErrorMessage } from "@/utils"
import GroupsList from "../Group/GroupsList.vue"
import TechniquesList from "../Technique/TechniquesList.vue"
import SoftwareDetails from "./SoftwareDetails.vue"

const { entity, id } = defineProps<{
	entity?: MitreSoftwareDetails
	id?: string
	fullWidth?: boolean
}>()

const emit = defineEmits<{
	(e: "loaded", value: MitreSoftwareDetails): void
}>()

const message = useMessage()
const loadingDetails = ref(false)
const fetchedSoftware = ref<MitreSoftwareDetails | undefined>(undefined)

const resolvedEntity = computed(() => entity ?? fetchedSoftware.value)

function getDetails(softwareId: string) {
	loadingDetails.value = true

	Api.wazuh.mitre
		.getMitreSoftware({ id: softwareId })
		.then(res => {
			if (res.data.success) {
				if (res.data.results?.[0]) {
					fetchedSoftware.value = res.data.results[0]
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
