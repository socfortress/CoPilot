<template>
	<n-button :size="size" :type="type" @click="showThreatIntelDrawer = true">Threat Intel</n-button>

	<n-drawer
		v-model:show="showThreatIntelDrawer"
		:width="500"
		style="max-width: 90vw"
		:trap-focus="false"
		display-directive="show"
	>
		<n-drawer-content title="SOCFortress Threat Intel" closable :native-scrollbar="false">
			<ThreatIntelForm @mounted="threatIntelCTX = $event" />
		</n-drawer-content>
	</n-drawer>
</template>

<script setup lang="ts">
import { ref, watch } from "vue"
import { NButton, NDrawer, NDrawerContent } from "naive-ui"
import ThreatIntelForm from "./ThreatIntelForm.vue"

const { type, size } = defineProps<{
	size?: "tiny" | "small" | "medium" | "large"
	type?: "default" | "tertiary" | "primary" | "info" | "success" | "warning" | "error"
}>()

const showThreatIntelDrawer = ref(false)
const threatIntelCTX = ref<{ restore: () => void } | null>(null)

watch(showThreatIntelDrawer, () => {
	threatIntelCTX.value?.restore()
})
</script>
