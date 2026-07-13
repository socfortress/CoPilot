<template>
	<n-spin :show="loadingDetails">
		<n-tabs v-if="resolvedEntity" type="line" animated :tabs-padding="fullWidth ? 0 : 24">
			<n-tab-pane name="Overview" tab="Overview" display-directive="show:lazy">
				<div :class="fullWidth ? 'p-0' : 'px-6 pt-3 pb-6'">
					<GroupDetails :entity="resolvedEntity" />
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
import type { MitreGroupDetails } from "@/types/mitre"
import { NSpin, NTabPane, NTabs, useMessage } from "naive-ui"
import { computed, onBeforeMount, ref } from "vue"
import Api from "@/api"
import { getApiErrorMessage } from "@/utils"
import SoftwareList from "../Software/SoftwareList.vue"
import TechniquesList from "../Technique/TechniquesList.vue"
import GroupDetails from "./GroupDetails.vue"

const { entity, id } = defineProps<{
	entity?: MitreGroupDetails
	id?: string
	fullWidth?: boolean
}>()

const emit = defineEmits<{
	(e: "loaded", value: MitreGroupDetails): void
}>()

const message = useMessage()
const loadingDetails = ref(false)
const fetchedGroup = ref<MitreGroupDetails | undefined>(undefined)

const resolvedEntity = computed(() => entity ?? fetchedGroup.value)

function getDetails(groupId: string) {
	loadingDetails.value = true

	Api.wazuh.mitre
		.getMitreGroups({ id: groupId })
		.then(res => {
			if (res.data.success) {
				if (res.data.results?.[0]) {
					fetchedGroup.value = res.data.results[0]
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
