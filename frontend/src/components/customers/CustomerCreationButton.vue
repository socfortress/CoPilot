<template>
	<n-button size="small" type="primary" @click="showAddCustomer = true">
		<template #icon>
			<Icon :name="AddUserIcon" :size="14"></Icon>
		</template>
		Add Customer
	</n-button>

	<n-drawer
		v-model:show="showAddCustomer"
		:width="500"
		style="max-width: 90vw"
		:trap-focus="false"
		display-directive="show"
	>
		<n-drawer-content title="Add Customer" closable :native-scrollbar="false">
			<CustomerForm :reset-on-submit="true" @mounted="customerFormCTX = $event" @submitted="emit('submitted')" />
		</n-drawer-content>
	</n-drawer>
</template>

<script setup lang="ts">
import Icon from "@/components/common/Icon.vue"
import { NButton, NDrawer, NDrawerContent } from "naive-ui"
import { ref, watch } from "vue"
import CustomerForm from "./CustomerForm.vue"

const emit = defineEmits<{
	(e: "submitted"): void
}>()

const openForm = defineModel<boolean | undefined>("openForm", { default: false })

const AddUserIcon = "carbon:user-follow"

const customerFormCTX = ref<{ reset: () => void } | null>(null)
const showAddCustomer = ref(false)

watch(showAddCustomer, val => {
	if (!val) {
		openForm.value = false
	}
	customerFormCTX.value?.reset()
})

watch(
	openForm,
	val => {
		if (val) {
			showAddCustomer.value = true
		}
	},
	{ immediate: true }
)
</script>
