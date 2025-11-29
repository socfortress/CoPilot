<template>
	<n-button :size="size" :type="type" @click="showForm = true">
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
		title="Deploy Content Packs"
		:bordered="false"
		segmented
	>
		<StackProvisioningList />
	</n-modal>
</template>

<script setup lang="ts">
import type { Size, Type } from "naive-ui/es/button/src/interface"
import { NButton, NModal } from "naive-ui"
import { ref } from "vue"
import Icon from "@/components/common/Icon.vue"
import StackProvisioningList from "./StackProvisioningList.vue"

const { type, size } = defineProps<{
	size?: Size
	type?: Type
}>()

const PackIcon = "mdi:package-variant"
const showForm = ref(false)
</script>
