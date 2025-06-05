<template>
	<n-button :size type="primary" secondary @click.stop="showForm = true">
		<template #icon>
			<Icon :name="AttackIcon" />
		</template>
		Simulate Attack
	</n-button>

	<n-modal
		v-model:show="showForm"
		display-directive="show"
		preset="card"
		:style="{ maxWidth: 'min(600px, 90vw)', minHeight: 'min(250px, 90vh)', overflow: 'hidden' }"
		:title="`${techniqueId}: Simulate Attack`"
		:bordered="false"
		segmented
		content-class="p-0!"
	>
		<SimulatorWizard :technique-id :os-list="checkedOsList" />
	</n-modal>
</template>

<script setup lang="ts">
import type { Size } from "naive-ui/es/button/src/interface"
import { NButton, NModal } from "naive-ui"
import { computed, ref } from "vue"
import Icon from "@/components/common/Icon.vue"
import SimulatorWizard from "./SimulatorWizard.vue"

const { size, techniqueId, osList } = defineProps<{ size?: Size; techniqueId: string; osList: string[] }>()

const AttackIcon = "mdi:target"
const showForm = ref(false)

const checkedOsList = computed(() => (osList?.length ? osList.filter(o => o.toLowerCase() !== "macos") : []))
</script>
