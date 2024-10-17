<template>
	<div
		class="license-subscription-feature-box"
		:class="{ embedded, disabled }"
		@click="selectable ? () => {} : (showDetails = true)"
	>
		<n-spin :show="canceling" content-class="px-4 py-3 flex flex-col gap-2">
			<div class="header-box flex items-center justify-between">
				<div class="flex cursor-pointer items-center gap-2">
					<span>{{ subscription.name }}</span>
					<span v-if="selectable" class="info-btn pt-0.5" @click.stop="showDetails = true">
						<Icon :name="InfoIcon" :size="14"></Icon>
					</span>
				</div>
				<div class="price">
					{{ price(subscription.price) }}
				</div>
			</div>
			<div v-if="!hideDetails" class="main-box flex items-center gap-3">
				<div class="content flex grow flex-col gap-2">
					<div class="title">
						{{ subscription.info }}
					</div>
					<div class="description">
						{{ subscription.short_description }}
					</div>
					<div v-if="showDeleteOnCard && licenseData" class="flex items-center justify-end">
						<n-popconfirm @positive-click="cancelSubscription()">
							<template #trigger>
								<n-button text size="small" class="opacity-50">
									<template #icon>
										<Icon :name="DeleteIcon" :size="16"></Icon>
									</template>
									Unsubscribe
								</n-button>
							</template>
							{{ deleteMessage }}
						</n-popconfirm>
					</div>
				</div>
			</div>
		</n-spin>

		<n-modal
			v-model:show="showDetails"
			preset="card"
			:style="{ maxWidth: 'min(600px, 90vw)', minHeight: 'min(300px, 90vh)', overflow: 'hidden' }"
			:title="subscription.name"
			:bordered="false"
			content-class="flex flex-col"
			segmented
		>
			<n-spin :show="canceling" content-class="flex flex-col gap-4 grow" class="flex grow flex-col">
				<div class="flex justify-between gap-4">
					<div>{{ subscription.info }}</div>
					<div class="text-primary-color whitespace-nowrap font-mono">
						{{ price(subscription.price) }}
					</div>
				</div>
				<div class="grow">
					{{ subscription.full_description }}
				</div>
				<div v-if="showDeleteOnDialog && licenseData" class="flex items-center justify-end">
					<n-popconfirm to="body" @positive-click="cancelSubscription()">
						<template #trigger>
							<n-button text size="small" class="opacity-50">
								<template #icon>
									<Icon :name="DeleteIcon" :size="16"></Icon>
								</template>
								Unsubscribe
							</n-button>
						</template>
						{{ deleteMessage }}
					</n-popconfirm>
				</div>
			</n-spin>
		</n-modal>
	</div>
</template>

<script setup lang="ts">
import type { CancelSubscriptionPayload } from "@/api/endpoints/license"
import type { License, SubscriptionFeature } from "@/types/license.d"
import Api from "@/api"
import Icon from "@/components/common/Icon.vue"
import { price } from "@/utils"
import { NButton, NModal, NPopconfirm, NSpin, useMessage } from "naive-ui"
import { ref, toRefs } from "vue"

const props = defineProps<{
	subscription: SubscriptionFeature
	embedded?: boolean
	selectable?: boolean
	disabled?: boolean
	hideDetails?: boolean
	showDeleteOnCard?: boolean
	showDeleteOnDialog?: boolean
	licenseData?: License
}>()

const emit = defineEmits<{
	(e: "deleted"): void
}>()

const { subscription, embedded, selectable, disabled, hideDetails, showDeleteOnCard, showDeleteOnDialog, licenseData } =
	toRefs(props)

const DeleteIcon = "ph:minus-circle"
const InfoIcon = "carbon:information"
const message = useMessage()
const showDetails = ref(false)
const deleteMessage = "Are you sure you want to give up this feature?"
const canceling = ref(false)

function cancelSubscription() {
	canceling.value = true

	const payload: CancelSubscriptionPayload = {
		customer_email: licenseData.value?.customer.email || "",
		subscription_price_id: subscription.value.subscription_price_id,
		feature_name: subscription.value.name
	}

	Api.license
		.cancelSubscription(payload)
		.then(res => {
			if (res.data.success) {
				emit("deleted")
			} else {
				message.warning(res.data?.message || "An error occurred. Please try again later.")
			}
		})
		.catch(err => {
			message.error(err.response?.data?.message || "An error occurred. Please try again later.")
		})
		.finally(() => {
			canceling.value = false
		})
}
</script>

<style lang="scss" scoped>
.license-subscription-feature-box {
	border-radius: var(--border-radius);
	background-color: var(--bg-color);
	border: var(--border-small-050);
	transition: all 0.2s var(--bezier-ease);
	cursor: pointer;

	.header-box {
		font-size: 13px;
		line-height: 1.25;
		.price {
			font-size: 15px;
			font-family: var(--font-family-mono);
			color: var(--primary-color);
		}

		.info-btn {
			&:hover {
				color: var(--primary-color);
			}
		}
	}

	.main-box {
		.content {
			word-break: break-word;

			.description {
				color: var(--fg-secondary-color);
				font-size: 13px;
			}
		}
	}

	&.embedded {
		background-color: var(--bg-secondary-color);
	}

	&.disabled {
		cursor: not-allowed;

		& > div {
			opacity: 0.5;
		}
	}

	&:not(.disabled) {
		&:hover {
			box-shadow: 0px 0px 0px 1px inset var(--primary-color);
		}
	}
}
</style>
