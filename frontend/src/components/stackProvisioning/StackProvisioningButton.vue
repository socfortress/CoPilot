<template>
	<n-button :size :type :secondary @click="openModal">
		<template #icon>
			<Icon :name="PackIcon" />
		</template>
		Stack Provisioning
	</n-button>

	<n-modal
		v-model:show="showForm"
		display-directive="show"
		preset="card"
		:style="{ maxWidth: 'min(600px, 90vw)', minHeight: 'min(300px, 90vh)', overflow: 'hidden' }"
		title="Stack Provisioning"
		:bordered="false"
		segmented
	>
		<n-tabs type="line" animated>
			<n-tab-pane name="graylog" tab="Graylog Content Packs" display-directive="show">
				<StackProvisioningList />
			</n-tab-pane>
			<n-tab-pane name="influxdb" tab="InfluxDB Checks" display-directive="show">
				<InfluxDbChecksList />
			</n-tab-pane>
		</n-tabs>
	</n-modal>
</template>

<script setup lang="ts">
import type { ButtonSize, ButtonType } from "naive-ui"
import { NButton, NModal, NTabPane, NTabs } from "naive-ui"
import { ref } from "vue"
import Icon from "@/components/common/Icon.vue"
import InfluxDbChecksList from "./influxdb/InfluxDbChecksList.vue"
import StackProvisioningList from "./StackProvisioningList.vue"

defineProps<{
	size?: ButtonSize
	type?: ButtonType
	secondary?: boolean
}>()

const PackIcon = "mdi:package-variant"
const showForm = ref(false)

function openModal() {
	showForm.value = true
}

function closeModal() {
	showForm.value = false
}

defineExpose({
	openModal,
	closeModal
})
</script>
