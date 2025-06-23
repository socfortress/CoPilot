<template>
	<div>
		<n-button :size @click.stop="showDetails = true">
			<template #icon>
				<Icon :name="MetaIcon"></Icon>
			</template>
			Meta Details
		</n-button>

		<n-modal
			v-model:show="showDetails"
			preset="card"
			:style="{ maxWidth: 'min(800px, 90vw)', minHeight: 'min(411px, 90vh)', overflow: 'hidden' }"
			content-class="flex flex-col"
			:title="`${integrationName}  —  Meta Details`"
			:bordered="false"
			segmented
			display-directive="show"
		>
			<CustomerIntegrationMetaDetails :customer-code :integration-name />
		</n-modal>
	</div>
</template>

<script setup lang="ts">
import type { Size } from "naive-ui/es/button/src/interface"
import { NButton, NModal } from "naive-ui"
import { defineAsyncComponent, ref } from "vue"
import Icon from "@/components/common/Icon.vue"

const { integrationName, customerCode, size } = defineProps<{
	integrationName: string
	customerCode: string
	size?: Size
}>()

const CustomerIntegrationMetaDetails = defineAsyncComponent(
	() => import("../metadata/CustomerIntegrationMetaDetails.vue")
)

const MetaIcon = "carbon:data-base"
const showDetails = ref(false)
</script>
