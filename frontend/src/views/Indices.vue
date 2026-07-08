<template>
	<div class="flex flex-col">
		<div class="mb-4 flex justify-end">
			<n-form-item label="Customer" :show-feedback="false" class="mb-0! w-full max-w-100">
				<n-select
					v-model:value="customerCodesFilter"
					:options="customersOptions"
					:loading="loadingCustomers"
					placeholder="All customers"
					multiple
					filterable
					clearable
				/>
			</n-form-item>
		</div>

		<div class="mb-6">
			<IndicesMarquee :indices @click="setIndex" />
		</div>

		<div class="mb-6">
			<Details v-model="currentIndex" :indices />
		</div>

		<div class="mb-6">
			<div class="flex gap-6 max-[1000px]:flex-col">
				<div class="basis-1/2">
					<ClusterHealth class="h-full" />
				</div>
				<div class="basis-1/2">
					<UnhealthyIndices :indices class="h-full" @click="setIndex" />
				</div>
			</div>
		</div>

		<div class="mb-6">
			<CustomerIndicesSize :customer-codes="customerCodesFilter" @click="setIndex" />
		</div>

		<n-card class="mb-6 overflow-hidden" content-class="p-0!">
			<div class="flex gap-0! max-[1200px]:flex-col">
				<div class="basis-2/5">
					<NodeAllocation class="h-full rounded-none" :bordered="false" />
				</div>
				<div class="basis-3/5 overflow-hidden">
					<TopIndices :indices class="rounded-none" :bordered="false" />
				</div>
			</div>
		</n-card>
	</div>
</template>

<script lang="ts" setup>
import type { ApiError } from "@/types/common"
import type { Customer } from "@/types/customers"
import type { IndexStats } from "@/types/indices"
import { NCard, NFormItem, NSelect, useMessage } from "naive-ui"
import { computed, defineAsyncComponent, onBeforeMount, ref, watch } from "vue"
import { useRoute } from "vue-router"
import Api from "@/api"
import ClusterHealth from "@/components/indices/ClusterHealth.vue"
import CustomerIndicesSize from "@/components/indices/CustomerIndicesSize.vue"
import Details from "@/components/indices/Details.vue"
import IndicesMarquee from "@/components/indices/Marquee.vue"
import NodeAllocation from "@/components/indices/NodeAllocation.vue"
import UnhealthyIndices from "@/components/indices/UnhealthyIndices.vue"
import { useGlobalCustomerFilter } from "@/composables/useGlobalCustomerFilter"
import { getApiErrorMessage } from "@/utils"

const TopIndices = defineAsyncComponent(() => import("@/components/indices/TopIndices.vue"))

const message = useMessage()
const route = useRoute()
const { applyGlobalCustomerPrefill } = useGlobalCustomerFilter()
const indices = ref<IndexStats[] | null>(null)
const loadingIndex = ref(false)
const loadingCustomers = ref(false)
const currentIndex = ref<IndexStats | null>(null)
const requestedIndex = ref<string | null>(null)
const customerCodesFilter = ref<string[]>([])
const customersList = ref<Customer[]>([])

const customersOptions = computed(() =>
	customersList.value.map(o => ({ label: `#${o.customer_code} - ${o.customer_name}`, value: o.customer_code }))
)

function setIndex(index: IndexStats | string) {
	if (typeof index === "string") {
		const indexStats = indices.value?.find(o => o.index === index) || null
		indexStats && (currentIndex.value = indexStats)
	} else {
		currentIndex.value = index
	}
}

function getCustomers() {
	loadingCustomers.value = true

	Api.customers
		.getCustomers()
		.then(res => {
			if (res.data.success) {
				customersList.value = res.data?.customers || []
			} else {
				message.error(res.data?.message || "An error occurred. Please try again later.")
			}
		})
		.catch(err => {
			message.error(getApiErrorMessage(err as ApiError) || "An error occurred. Please try again later.")
		})
		.finally(() => {
			loadingCustomers.value = false
		})
}

function getIndices(cb?: () => void) {
	loadingIndex.value = true

	const query = customerCodesFilter.value.length ? { customerCodes: customerCodesFilter.value } : undefined

	Api.wazuh.indices
		.getIndices(query)
		.then(res => {
			if (res.data.success) {
				indices.value = res.data.indices_stats

				if (cb) cb()
			} else {
				message.error(res.data?.message || "An error occurred. Please try again later.")
			}
		})
		.catch(err => {
			if (err.response?.status === 401) {
				message.error(
					getApiErrorMessage(err as ApiError) ||
						"Wazuh-Indexer returned Unauthorized. Please check your connector credentials."
				)
			} else if (err.response?.status === 404) {
				message.error(getApiErrorMessage(err as ApiError) || "No indices were found.")
			} else {
				message.error(getApiErrorMessage(err as ApiError) || "An error occurred. Please try again later.")
			}
		})
		.finally(() => {
			loadingIndex.value = false
		})
}

onBeforeMount(() => {
	if (route.query?.index_name) {
		requestedIndex.value = route.query.index_name.toString()
	}

	getCustomers()

	const draft = { customerCodes: customerCodesFilter.value }
	applyGlobalCustomerPrefill("customerCodes", draft, { multiple: true })
	customerCodesFilter.value = (draft.customerCodes as string[]) || []
})

watch(
	() => customerCodesFilter.value,
	() => {
		getIndices(() => {
			if (requestedIndex.value) {
				setIndex(requestedIndex.value)
			} else if (currentIndex.value) {
				setIndex(currentIndex.value.index)
			}
		})
	},
	{ immediate: true }
)
</script>
