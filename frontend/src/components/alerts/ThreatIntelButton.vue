<template>
	<n-button :size="size" :type="type" @click="showThreatIntelDrawer = true">
		<template #icon><Icon :name="ThreatIcon"></Icon></template>
		Threat Intel
	</n-button>

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
import Icon from "@/components/common/Icon.vue"
import type { Size, Type } from "naive-ui/es/button/src/interface"

const { type, size } = defineProps<{
	size?: Size
	type?: Type
}>()

const ThreatIcon = "mynaui:info-waves"
const showThreatIntelDrawer = ref(false)
const threatIntelCTX = ref<{ restore: () => void } | null>(null)

watch(showThreatIntelDrawer, () => {
	threatIntelCTX.value?.restore()
})
</script>
