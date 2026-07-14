<template>
	<div class="page">
		<CustomersList
			:reload
			@loaded="
				(() => {
					customersCount = $event
					reload = false
					firstLoad = true
				})()
			"
		>
			<CustomerDefaultSettingsButton />
			<CustomerCreationButton
				v-model:open-form="openForm"
				:customers-count
				:disabled="!firstLoad"
				@submitted="reload = true"
			/>
		</CustomersList>
	</div>
</template>

<script setup lang="ts">
import { onBeforeMount, onMounted, onUnmounted, ref } from "vue"
import { useRoute } from "vue-router"
import CustomerCreationButton from "@/components/customers/CustomerCreationButton.vue"
import CustomersList from "@/components/customers/CustomersList.vue"
import CustomerDefaultSettingsButton from "@/components/customers/provision/CustomerDefaultSettingsButton.vue"
import { useNavigation } from "@/composables/useNavigation"
import { useSearchDialog } from "@/composables/useSearchDialog"

const route = useRoute()
const { routeCustomer } = useNavigation()

const reload = ref(false)
const firstLoad = ref(false)
const openForm = ref(false)
const customersCount = ref<undefined | number>(undefined)

function setOpenForm() {
	if (!openForm.value) {
		openForm.value = true
		routeCustomer().replace()
	}
}

onBeforeMount(() => {
	if (route.query?.code) {
		routeCustomer({ code: route.query.code.toString() }).replace()
		return
	}

	if (route.query?.action === "add-customer") {
		setOpenForm()
	}
})

let unregisterAddCustomer: (() => void) | undefined

onMounted(() => {
	unregisterAddCustomer = useSearchDialog().registerAddCustomer(setOpenForm)
})
onUnmounted(() => {
	unregisterAddCustomer?.()
})
</script>
