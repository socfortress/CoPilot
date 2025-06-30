<template>
	<n-button :size="size" :type="type" @click="showThreatIntelDrawer = true">
		<template #icon>
			<Icon :name="ThreatIcon"></Icon>
		</template>
		Threat Intel
	</n-button>

	<n-drawer
		v-model:show="showThreatIntelDrawer"
		:width="500"
		style="max-width: 90vw"
		:trap-focus="false"
		:close-on-esc="false"
		:mask-closable="false"
		display-directive="show"
	>
		<n-drawer-content title="Threat Intel" closable :native-scrollbar="false">
			<div class="py-3">
				<n-collapse default-expanded-names="1" accordion display-directive="show">
					<n-collapse-item title="SOCFortress Threat Intel" name="1">
						<ThreatIntelForm @mounted="threatIntelCTX = $event" />
					</n-collapse-item>
					<n-collapse-item title="Virus Total" name="2">
						<VirusTotalForm @mounted="virusTotalCTX = $event" />
					</n-collapse-item>
				</n-collapse>
			</div>
		</n-drawer-content>
	</n-drawer>
</template>

<script setup lang="ts">
import type { Size, Type } from "naive-ui/es/button/src/interface"
import { NButton, NCollapse, NCollapseItem, NDrawer, NDrawerContent } from "naive-ui"
import { ref, watch } from "vue"
import Icon from "@/components/common/Icon.vue"
import ThreatIntelForm from "./ThreatIntelForm.vue"
import VirusTotalForm from "./VirusTotalForm.vue"

const { type, size } = defineProps<{
	size?: Size
	type?: Type
}>()

const ThreatIcon = "mynaui:info-waves"
const showThreatIntelDrawer = ref(false)
const threatIntelCTX = ref<{ restore: () => void } | null>(null)
const virusTotalCTX = ref<{ restore: () => void } | null>(null)

watch(showThreatIntelDrawer, () => {
	threatIntelCTX.value?.restore()
	virusTotalCTX.value?.restore()
})
</script>
