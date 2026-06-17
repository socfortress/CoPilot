<template>
	<div class="customers-list">
		<div class="header mb-4 flex items-center justify-between gap-2">
			<div class="flex items-center gap-4">
				<div>
					Total:
					<strong class="font-mono">{{ totalCustomers }}</strong>
				</div>
				<div class="flex items-center gap-2">
					<span class="shrink-0 text-sm">Sort by:</span>
					<n-select
						v-model:value="sortField"
						:options="sortFieldOptions"
						size="small"
						class="w-30"
						:consistent-menu-width="false"
					/>
					<n-select
						v-model:value="sortOrder"
						:options="sortOrderOptions"
						size="small"
						:show-checkmark="false"
						class="max-w-20"
						:consistent-menu-width="false"
					/>
				</div>
			</div>
			<div class="flex items-center gap-3">
				<slot></slot>
			</div>
		</div>
		<n-spin :show="loadingCustomers">
			<div class="min-h-52">
				<template v-if="sortedCustomersList.length">
					<CustomerItem
						v-for="customer of sortedCustomersList"
						:key="customer.customer_code"
						:customer
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
import type { ApiError } from "@/types/common"
import type { Customer } from "@/types/customers.d"
import { NEmpty, NSelect, NSpin, useMessage } from "naive-ui"
import { computed, nextTick, onBeforeMount, ref, toRefs, watch } from "vue"
import Api from "@/api"
import { getApiErrorMessage } from "@/utils"
import CustomerItem from "./CustomerItem.vue"

const props = defineProps<{ highlight: string | null | undefined; reload?: boolean }>()
const emit = defineEmits<{
	(e: "loaded", value: number): void
}>()

const { highlight, reload } = toRefs(props)

const message = useMessage()
const loadingCustomers = ref(false)
const customersList = ref<Customer[]>([])
const sortField = ref<"id" | "name">("id")
const sortOrder = ref<"asc" | "desc">("asc")

const sortFieldOptions = [
	{ label: "ID", value: "id" },
	{ label: "Name", value: "name" }
]

const sortOrderOptions = [
	{ label: "Asc", value: "asc" },
	{ label: "Desc", value: "desc" }
]

const totalCustomers = computed<number>(() => {
	return customersList.value.length || 0
})

const sortedCustomersList = computed<Customer[]>(() => {
	const customers = [...customersList.value]

	if (sortField.value === "name") {
		return customers.sort((a, b) => {
			const cmp = a.customer_name.toLowerCase().localeCompare(b.customer_name.toLowerCase())
			return sortOrder.value === "asc" ? cmp : -cmp
		})
	}

	return sortOrder.value === "desc" ? customers.reverse() : customers
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
			message.error(getApiErrorMessage(err as ApiError) || "An error occurred. Please try again later.")
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
