<template>
	<div>
		<n-button :size @click.stop="showDetails = true">
			<template #icon>
				<Icon :name="MetaIcon" />
			</template>
			Meta Details
		</n-button>

		<n-modal
			v-model:show="showDetails"
			preset="card"
			:style="{ maxWidth: 'min(800px, 90vw)', minHeight: 'min(411px, 90vh)', overflow: 'hidden' }"
			content-class="flex flex-col"
			:title="modalTitle"
			:bordered="false"
			segmented
			display-directive="show"
		>
			<CustomerIntegrationMetaDetails :customer-code :integration-name :instance-name />
		</n-modal>
	</div>
</template>

<script setup lang="ts">
import type { ButtonSize } from "naive-ui"
import { NButton, NModal } from "naive-ui"
import { computed, defineAsyncComponent, ref } from "vue"
import Icon from "@/components/common/Icon.vue"

const { integrationName, customerCode, instanceName, size } = defineProps<{
	integrationName: string
	customerCode: string
	/** Which instance's metadata to show, for an integration a customer holds more than one of */
	instanceName?: string | null
	size?: ButtonSize
}>()

const CustomerIntegrationMetaDetails = defineAsyncComponent(
	() => import("../metadata/CustomerIntegrationMetaDetails.vue")
)

const MetaIcon = "carbon:data-base"
const showDetails = ref(false)
const modalTitle = computed(() =>
	instanceName ? `${integrationName} — ${instanceName}  —  Meta Details` : `${integrationName}  —  Meta Details`
)
</script>
