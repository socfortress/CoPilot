<template>
	<n-spin :show="loadingDetails">
		<n-tabs v-if="resolvedEntity" type="line" animated :tabs-padding="fullWidth ? 0 : 24">
			<n-tab-pane name="Overview" tab="Overview" display-directive="show:lazy">
				<div :class="fullWidth ? 'p-0' : 'px-6 pt-3 pb-6'">
					<MitigationDetails :entity="resolvedEntity" />
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
import type { MitreMitigationDetails } from "@/types/mitre"
import { NSpin, NTabPane, NTabs, useMessage } from "naive-ui"
import { computed, onBeforeMount, ref } from "vue"
import Api from "@/api"
import { getApiErrorMessage } from "@/utils"
import TechniquesList from "../Technique/TechniquesList.vue"
import MitigationDetails from "./MitigationDetails.vue"

const { entity, id } = defineProps<{
	entity?: MitreMitigationDetails
	id?: string
	fullWidth?: boolean
}>()

const emit = defineEmits<{
	(e: "loaded", value: MitreMitigationDetails): void
}>()

const message = useMessage()
const loadingDetails = ref(false)
const fetchedMitigation = ref<MitreMitigationDetails | undefined>(undefined)

const resolvedEntity = computed(() => entity ?? fetchedMitigation.value)

function getDetails(mitigationId: string) {
	loadingDetails.value = true

	Api.wazuh.mitre
		.getMitreMitigations({ id: mitigationId })
		.then(res => {
			if (res.data.success) {
				if (res.data.results?.[0]) {
					fetchedMitigation.value = res.data.results[0]
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
