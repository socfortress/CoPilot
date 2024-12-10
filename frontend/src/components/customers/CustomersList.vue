<template>
	<div class="customers-list">
		<div class="header mb-4 flex items-center justify-between gap-2">
			<div>
				Total:
				<strong class="font-mono">{{ totalCustomers }}</strong>
			</div>
			<div class="flex items-center gap-3">
				<slot></slot>
			</div>
		</div>
		<n-spin :show="loadingCustomers">
			<div class="min-h-52">
				<template v-if="customersList.length">
					<CustomerItem
						v-for="customer of customersList"
						:key="customer.customer_code"
						:customer="customer"
						:highlight="customer.customer_code === highlight"
						:hide-card-actions="loadingCustomers"
						class="item-appear item-appear-bottom item-appear-005 mb-2"
						@delete="getCustomers()"
					/>
				</template>
				<template v-else>
					<n-empty v-if="!loadingCustomers" description="No items found" class="h-48 justify-center" />
				</template>
			</div>
		</n-spin>
	</div>
</template>

<script setup lang="ts">
import type { Customer } from "@/types/customers.d"
import Api from "@/api"
import { NEmpty, NSpin, useMessage } from "naive-ui"
import { computed, nextTick, onBeforeMount, ref, toRefs, watch } from "vue"
import CustomerItem from "./CustomerItem.vue"

const props = defineProps<{ highlight: string | null | undefined; reload?: boolean }>()
const emit = defineEmits<{
	(e: "loaded", value: number): void
}>()

const { highlight, reload } = toRefs(props)

const message = useMessage()
const loadingCustomers = ref(false)
const customersList = ref<Customer[]>([])

const totalCustomers = computed<number>(() => {
	return customersList.value.length || 0
})

function getCustomers() {
	loadingCustomers.value = true

	Api.customers
		.getCustomers()
		.then(res => {
			if (res.data.success) {
				customersList.value = res.data?.customers || []
				emit("loaded", customersList.value.length || 0)
			} else {
				message.warning(res.data?.message || "An error occurred. Please try again later.")
			}
		})
		.catch(err => {
			message.error(err.response?.data?.message || "An error occurred. Please try again later.")
		})
		.finally(() => {
			loadingCustomers.value = false
		})
}

function scrollToItem(id: string) {
	const element = document.getElementById(`customer-${id}`)
	const scrollContent = document.querySelector("#main > .n-scrollbar > .n-scrollbar-container") as HTMLElement

	if (element && scrollContent) {
		const wrap: HTMLElement = scrollContent
		const middle = element.offsetTop - wrap.offsetHeight / 2
		scrollContent?.scrollTo({ top: middle, behavior: "smooth" })
	}
}

watch(reload, val => {
	if (val) {
		getCustomers()
	}
})

watch(loadingCustomers, val => {
	if (!val) {
		nextTick(() => {
			setTimeout(() => {
				if (highlight.value) {
					scrollToItem(highlight.value)
				}
			}, 300)
		})
	}
})

watch(highlight, val => {
	if (val) {
		nextTick(() => {
			setTimeout(() => {
				scrollToItem(val)
			})
		})
	}
})

onBeforeMount(() => {
	getCustomers()
})
</script>
