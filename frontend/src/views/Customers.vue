<template>
	<div class="page">
		<CustomersList :highlight="highlight" :reload="reload" @reloaded="reload = false">
			<CustomerDefaultSettingsButton />
			<CustomerCreationButton v-model:open-form="openForm" @submitted="reload = true" />
		</CustomersList>
	</div>
</template>

<script setup lang="ts">
import CustomerCreationButton from "@/components/customers/CustomerCreationButton.vue"
import CustomersList from "@/components/customers/CustomersList.vue"
import CustomerDefaultSettingsButton from "@/components/customers/provision/CustomerDefaultSettingsButton.vue"
import { emitter } from "@/emitter"
import { onBeforeMount, onMounted, onUnmounted, ref } from "vue"
import { useRoute, useRouter } from "vue-router"

const route = useRoute()
const router = useRouter()

const highlight = ref<string | undefined>(undefined)
const reload = ref(false)
const openForm = ref(false)

function setOpenForm() {
	if (!openForm.value) {
		openForm.value = true
		router.replace({ name: "Customers" })
	}
}

onBeforeMount(() => {
	if (route.query?.code) {
		highlight.value = route.query.code.toString()
	}

	if (route.query?.action === "add-customer") {
		setOpenForm()
	}
})

onMounted(() => {
	emitter.on("action:add-customer", setOpenForm)
})
onUnmounted(() => {
	emitter.off("action:add-customer", setOpenForm)
})
</script>
