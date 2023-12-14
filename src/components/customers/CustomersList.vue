<template>
	<div class="customers-list">
		<div class="header mb-4 flex gap-2">
			<span>
				Total:
				<strong class="font-mono">{{ totalCustomers }}</strong>
			</span>
		</div>
		<n-spin :show="loadingCustomers">
			<div class="list">
				<template v-if="customersList.length">
					<CustomerItem
						v-for="customer of customersList"
						:key="customer.customer_code"
						:customer="customer"
						:highlight="customer.customer_code === highlight"
						class="mb-2"
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
// TODO: merge of customer-item-fade (*-fade) animations

import { ref, onBeforeMount, computed, watch, toRefs, nextTick } from "vue"
import { useMessage, NSpin, NEmpty } from "naive-ui"
import Api from "@/api"
import CustomerItem from "./CustomerItem.vue"
import type { Customer } from "@/types/customers.d"

const props = defineProps<{ highlight: string | null | undefined }>()
const { highlight } = toRefs(props)

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
		})
}

function scrollToAlert(id: string) {
	const element = document.getElementById(`customer-${id}`)
	const scrollContent = document.querySelector("#main > .n-scrollbar > .n-scrollbar-container") as HTMLElement

	if (element && scrollContent) {
		const wrap: HTMLElement = scrollContent
		const middle = element.offsetTop - wrap.offsetHeight / 2
		scrollContent?.scrollTo({ top: middle, behavior: "smooth" })
	}
}

watch(loadingCustomers, val => {
	if (!val) {
		nextTick(() => {
			setTimeout(() => {
				if (highlight.value) {
					scrollToAlert(highlight.value)
				}
			}, 300)
		})
	}
})

watch(highlight, val => {
	if (val) {
		nextTick(() => {
			setTimeout(() => {
				scrollToAlert(val)
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

		.customer-item {
			animation: customer-item-fade 0.3s forwards;
			opacity: 0;

			@for $i from 0 through 30 {
				&:nth-child(#{$i}) {
					animation-delay: $i * 0.05s;
				}
			}

			@keyframes customer-item-fade {
				from {
					opacity: 0;
					transform: translateY(10px);
				}
				to {
					opacity: 1;
				}
			}
		}
	}
}
</style>
