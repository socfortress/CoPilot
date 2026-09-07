<template>
	<div class="page">
		<n-alert v-if="isFiltering" type="info" :bordered="false" class="mb-4 text-xs">
			The global customers filter ({{ globalCustomerCodes.join(", ") }}) is not applied here. This
			page always lists every customer your account has access to — what you can see is decided by
			your customer assignments, not by this filter.
		</n-alert>

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
import { NAlert } from "naive-ui"
import { onBeforeMount, onMounted, onUnmounted, ref } from "vue"
import { useRoute } from "vue-router"
import CustomerCreationButton from "@/components/customers/CustomerCreationButton.vue"
import CustomersList from "@/components/customers/CustomersList.vue"
import CustomerDefaultSettingsButton from "@/components/customers/provision/CustomerDefaultSettingsButton.vue"
import { useGlobalCustomerFilter } from "@/composables/useGlobalCustomerFilter"
import { useNavigation } from "@/composables/useNavigation"
import { useSearchDialog } from "@/composables/useSearchDialog"

const route = useRoute()
const { routeCustomer } = useNavigation()
// The sidebar filter narrows other views; this one is the source of truth for *access*, so it
// deliberately ignores it. Saying so only when a selection exists keeps the page quiet the rest
// of the time, and answers the question exactly when someone is in a position to ask it.
const { isFiltering, globalCustomerCodes } = useGlobalCustomerFilter()

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
