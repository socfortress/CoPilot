<template>
	<n-button size="small" type="primary" secondary @click="showForm = true" :loading="loading">
		<div class="flex items-center gap-2">
			<Icon :name="DangerIcon" :size="18"></Icon>
			<span class="hidden xs:block">Custom Alert</span>
		</div>
	</n-button>

	<n-modal
		v-model:show="showForm"
		display-directive="show"
		preset="card"
		:style="{ maxWidth: 'min(600px, 90vw)', minHeight: 'min(300px, 90vh)', overflow: 'hidden' }"
		title="Create a Custom Alert"
		:bordered="false"
		segmented
	>
		<CustomAlertForm @mounted="formCTX = $event" v-model:loading="loading" />
	</n-modal>
</template>

<script setup lang="ts">
import { ref, watch } from "vue"
import { NButton, NModal } from "naive-ui"
import Icon from "@/components/common/Icon.vue"
import CustomAlertForm from "./CustomAlertForm.vue"

const DangerIcon = "majesticons:exclamation-line"

const formCTX = ref<{ reset: () => void } | null>(null)
const showForm = ref(false)
const loading = ref(false)

watch(showForm, val => {
	if (val) {
		formCTX.value?.reset()
	}
})
</script>
