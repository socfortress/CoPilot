<template>
	<n-button size="small" secondary @click="showForm = true" :loading="loading">
		<template #icon>
			<Icon :name="SettingsIcon" :size="14"></Icon>
		</template>
		Default Settings
	</n-button>

	<n-modal
		v-model:show="showForm"
		display-directive="show"
		preset="card"
		:style="{ maxWidth: 'min(600px, 90vw)', minHeight: 'min(300px, 90vh)', overflow: 'hidden' }"
		title="Customer Provisioning Default Settings"
		:bordered="false"
		segmented
	>
		<CustomerDefaultSettingsForm @mounted="settingsFormCTX = $event" v-model:loading="loading" />
	</n-modal>
</template>

<script setup lang="ts">
import { ref, watch } from "vue"
import { NButton, NModal } from "naive-ui"
import Icon from "@/components/common/Icon.vue"
import CustomerDefaultSettingsForm from "./CustomerDefaultSettingsForm.vue"

const SettingsIcon = "carbon:settings-edit"
const settingsFormCTX = ref<{ load: () => void } | null>(null)
const showForm = ref(false)
const loading = ref(false)

watch(showForm, val => {
	if (val) {
		settingsFormCTX.value?.load()
	}
})
</script>
