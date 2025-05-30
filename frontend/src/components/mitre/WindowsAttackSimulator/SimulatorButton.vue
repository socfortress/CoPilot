<template>
	<n-button :size type="primary" secondary @click="showForm = true">
		<template #icon>
			<Icon :name="AttackIcon" />
		</template>
		Simulate Windows Attack
	</n-button>

	<n-modal
		v-model:show="showForm"
		display-directive="show"
		preset="card"
		:style="{ maxWidth: 'min(600px, 90vw)', minHeight: 'min(240px, 90vh)', overflow: 'hidden' }"
		title="Simulate Windows Attack"
		:bordered="false"
		segmented
	>
		<SimulatorWizard :technique-id />
	</n-modal>
</template>

<script setup lang="ts">
import type { Size } from "naive-ui/es/button/src/interface"
import { NButton, NModal } from "naive-ui"
import { ref } from "vue"
import Icon from "@/components/common/Icon.vue"
import SimulatorWizard from "./SimulatorWizard.vue"

const { size, techniqueId } = defineProps<{ size?: Size; techniqueId: string }>()

const AttackIcon = "mdi:target"
const showForm = ref(false)
</script>
