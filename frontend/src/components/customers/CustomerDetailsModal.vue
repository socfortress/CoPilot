<template>
	<n-modal
		v-model:show="show"
		preset="card"
		content-class="p-0!"
		:style="{ maxWidth: 'min(1100px, 90vw)', minHeight: 'min(470px, 90vh)', overflow: 'hidden' }"
		:title="title || customerCode || ''"
		:bordered="false"
		segmented
	>
		<template #header-extra>
			<ModalPageButton
				v-if="customerCode"
				:route="routeCustomer({ code: customerCode })"
				label="Open the customer's page"
				@navigate="show = false"
			/>
		</template>
		<CustomerDetails v-if="show && customerCode" :customer-code use-max-height @delete="deleted()" />
	</n-modal>
</template>

<script setup lang="ts">
import { NModal } from "naive-ui"
import { defineAsyncComponent } from "vue"
import ModalPageButton from "@/components/common/ModalPageButton.vue"
import { useNavigation } from "@/composables/useNavigation"

/** One customer in a modal, by code, linking its page from the header. */
const { customerCode, title } = defineProps<{
	customerCode: string | null
	title?: string
}>()

const emit = defineEmits<{
	/** The customer was deleted from the modal. */
	(e: "deleted"): void
}>()

const show = defineModel<boolean>("show", { default: false })

const CustomerDetails = defineAsyncComponent(() => import("./CustomerDetails.vue"))

const { routeCustomer } = useNavigation()

function deleted() {
	show.value = false
	emit("deleted")
}
</script>
