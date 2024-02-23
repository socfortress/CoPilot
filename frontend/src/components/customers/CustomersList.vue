<template>
	<div class="customers-list">
		<div class="header mb-4 flex gap-2 justify-between items-center">
			<div>
				Total:
				<strong class="font-mono">{{ totalCustomers }}</strong>
			</div>
			<div class="flex items-center gap-3">
				<slot></slot>
			</div>
		</div>
		<n-spin :show="loadingCustomers">
			<div class="list">
				<template v-if="customersList.length">
					<CustomerItem
						v-for="customer of customersList"
						:key="customer.customer_code"
						:customer="customer"
						:highlight="customer.customer_code === highlight"
						:hideCardActions="loadingCustomers"
						@delete="getCustomers()"
						class="item-appear item-appear-bottom item-appear-005 mb-2"
					/>
				</template>
				<template v-else>
					<n-empty description="No items found" class="justify-center h-48" v-if="!loadingCustomers" />
				</template>
			</div>
		</n-spin>
	</div>
</template>

<script setup lang="ts">
import { ref, onBeforeMount, computed, watch, toRefs, nextTick } from "vue"
import { useMessage, NSpin, NEmpty } from "naive-ui"
import Api from "@/api"
import CustomerItem from "./CustomerItem.vue"
import type { Customer } from "@/types/customers.d"

const props = defineProps<{ highlight: string | null | undefined; reload?: boolean }>()
const { highlight, reload } = toRefs(props)

const emit = defineEmits<{
	(e: "reloaded"): void
}>()

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
			} else {
				message.warning(res.data?.message || "An error occurred. Please try again later.")
			}
		})
		.catch(err => {
			message.error(err.response?.data?.message || "An error occurred. Please try again later.")
		})
		.finally(() => {
			loadingCustomers.value = false
			emit("reloaded")
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

<style lang="scss" scoped>
.customers-list {
	.list {
		container-type: inline-size;
		min-height: 200px;
	}
}
</style>
