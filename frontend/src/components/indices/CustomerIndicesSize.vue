<template>
	<n-card title="Storage per Customer" segmented content-class="pr-1!">
		<n-spin :show="loading">
			<div v-if="customerSizes && customerSizes.length > 0">
				<n-scrollbar class="max-h-50" trigger="none" content-class="flex flex-col gap-4 pr-5!">
					<div v-for="customer in customerSizes" :key="customer.customer" class="flex flex-col gap-1">
						<div class="flex items-center justify-between gap-2">
							<div class="flex items-center gap-2">
								<div class="font-mono font-bold">{{ customer.customer }}</div>
								<n-popover trigger="click" placement="bottom" :width="300">
									<template #trigger>
										<n-tag size="small" class="cursor-pointer!">
											{{ customer.index_count }}
											{{ customer.index_count === 1 ? "index" : "indices" }}
										</n-tag>
									</template>
									<div class="flex flex-col gap-2">
										<span class="text-sm font-semibold">Indices for {{ customer.customer }}</span>
										<n-scrollbar class="max-h-50" trigger="none">
											<ul>
												<li
													v-for="index in customer.indices"
													:key="index"
													@click="selectIndex(index)"
												>
													<div
														class="hover:text-primary flex cursor-pointer items-center gap-2 font-mono text-sm transition-colors"
													>
														{{ index }}

														<Icon name="carbon:launch" />
													</div>
												</li>
											</ul>
										</n-scrollbar>
									</div>
								</n-popover>
							</div>
							<div class="text-secondary font-mono text-sm">{{ customer.total_size_human }}</div>
						</div>
						<n-progress
							type="line"
							:percentage="getPercentage(customer.total_size_bytes)"
							:show-indicator="false"
							:height="8"
							:border-radius="4"
							:color="getProgressColor(customer.total_size_bytes)"
						/>
					</div>
				</n-scrollbar>
			</div>
			<n-empty v-else-if="!loading" description="No customer data available" />
		</n-spin>
	</n-card>
</template>

<script lang="ts" setup>
import type { ApiError } from "@/types/common"
import type { CustomerIndicesSize } from "@/types/indices"
import { NCard, NEmpty, NPopover, NProgress, NScrollbar, NSpin, NTag, useMessage, useThemeVars } from "naive-ui"
import { computed, ref, toRefs, watch } from "vue"
import Api from "@/api"
import Icon from "@/components/common/Icon.vue"
import { getApiErrorMessage } from "@/utils"

const props = defineProps<{
	customerCodes?: string[]
}>()

const emit = defineEmits<{
	(e: "click", value: string): void
}>()

const { customerCodes } = toRefs(props)
const message = useMessage()
const themeVars = useThemeVars()

const loading = ref(false)
const customerSizes = ref<CustomerIndicesSize[]>([])

const maxSize = computed(() => {
	if (!customerSizes.value.length) return 0
	return Math.max(...customerSizes.value.map(c => c.total_size_bytes))
})

function getPercentage(sizeBytes: number): number {
	if (!maxSize.value) return 0
	return Math.round((sizeBytes / maxSize.value) * 100)
}

function getProgressColor(sizeBytes: number): string {
	const percentage = getPercentage(sizeBytes)
	if (percentage >= 80) return themeVars.value.errorColor
	if (percentage >= 60) return themeVars.value.warningColor
	return themeVars.value.infoColor
}

function selectIndex(indexName: string) {
	emit("click", indexName)
}

function getCustomerIndicesSize() {
	loading.value = true

	const query = customerCodes.value?.length ? { customerCodes: customerCodes.value } : undefined

	Api.wazuh.indices
		.getIndicesSizePerCustomer(query)
		.then(res => {
			if (res.data.success) {
				customerSizes.value = res.data.customer_sizes || []
			} else {
				message.error(res.data?.message || "An error occurred. Please try again later.")
			}
		})
		.catch(err => {
			message.error(getApiErrorMessage(err as ApiError) || "Failed to retrieve customer indices size.")
		})
		.finally(() => {
			loading.value = false
		})
}

watch(
	() => customerCodes.value,
	() => {
		getCustomerIndicesSize()
	},
	{ deep: true, immediate: true }
)
</script>
