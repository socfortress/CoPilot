<template>
	<n-button size="small" secondary :loading="loading" @click="(showForm = true)">
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
		<CustomerDefaultSettingsForm v-model:loading="loading" @mounted="(settingsFormCTX = $event)" />
	</n-modal>
</template>

<script setup lang="ts">
import Icon from "@/components/common/Icon.vue"
import { NButton, NModal } from "naive-ui"
import { ref, watch } from "vue"
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
