<template>
	<n-card title="Storage per Customer" :bordered="bordered">
		<n-spin :show="loading">
			<div v-if="customerSizes && customerSizes.length > 0" class="customer-list">
				<div v-for="customer in customerSizes" :key="customer.customer" class="customer-item">
					<div class="customer-header">
						<div class="customer-name">
							<n-text strong>{{ customer.customer }}</n-text>
							<n-popover trigger="click" placement="bottom" :width="300">
								<template #trigger>
									<n-tag
										size="small"
										:bordered="false"
										type="info"
										class="clickable-tag"
									>
										{{ customer.index_count }} {{ customer.index_count === 1 ? "index" : "indices" }}
									</n-tag>
								</template>
								<div class="indices-popover">
									<div class="popover-header">
										<n-text strong>Indices for {{ customer.customer }}</n-text>
									</div>
									<n-scrollbar style="max-height: 200px">
										<div class="indices-list">
											<div
												v-for="index in customer.indices"
												:key="index"
												class="index-item"
												@click="selectIndex(index)"
											>
												<n-text code class="index-link">{{ index }}</n-text>
											</div>
										</div>
									</n-scrollbar>
								</div>
							</n-popover>
						</div>
						<n-text class="customer-size">{{ customer.total_size_human }}</n-text>
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
			</div>
			<n-empty v-else-if="!loading" description="No customer data available" />
		</n-spin>
	</n-card>
</template>

<script lang="ts" setup>
import { NCard, NEmpty, NPopover, NProgress, NScrollbar, NSpin, NTag, NText, useMessage, useThemeVars } from "naive-ui"
import { computed, onBeforeMount, ref } from "vue"
import Api from "@/api"

interface CustomerIndicesSize {
    customer: string
    total_size_bytes: number
    total_size_human: string
    index_count: number
    indices: string[]
}

defineProps<{
    bordered?: boolean
}>()

const emit = defineEmits<{
    (e: "click", value: string): void
}>()

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
    return themeVars.value.primaryColor
}

function selectIndex(indexName: string) {
    emit("click", indexName)
}

function getCustomerIndicesSize() {
    loading.value = true

    Api.wazuh.indices
        .getIndicesSizePerCustomer()
        .then(res => {
            if (res.data.success) {
                customerSizes.value = res.data.customer_sizes || []
            } else {
                message.error(res.data?.message || "An error occurred. Please try again later.")
            }
        })
        .catch(err => {
            message.error(err.response?.data?.message || "Failed to retrieve customer indices size.")
        })
        .finally(() => {
            loading.value = false
        })
}

onBeforeMount(() => {
    getCustomerIndicesSize()
})
</script>

<style lang="scss" scoped>
.customer-list {
    display: flex;
    flex-direction: column;
    gap: 16px;
    max-height: 400px;
    overflow-y: auto;

    .customer-item {
        .customer-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 6px;

            .customer-name {
                display: flex;
                align-items: center;
                gap: 8px;

                .clickable-tag {
                    cursor: pointer;
                    transition: opacity 0.2s;

                    &:hover {
                        opacity: 0.8;
                    }
                }
            }

            .customer-size {
                font-weight: 600;
                font-family: var(--font-family-mono);
            }
        }
    }
}

.indices-popover {
    .popover-header {
        margin-bottom: 8px;
        padding-bottom: 8px;
        border-bottom: 1px solid var(--border-color);
    }

    .indices-list {
        display: flex;
        flex-direction: column;
        gap: 4px;

        .index-item {
            padding: 4px 0;
            cursor: pointer;
            border-radius: 4px;
            transition: background-color 0.2s;

            &:hover {
                background-color: var(--hover-color);
            }

            .index-link {
                cursor: pointer;
            }
        }
    }
}
</style>
