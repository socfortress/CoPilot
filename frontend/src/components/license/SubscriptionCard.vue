<template>
	<div>
		<CardEntity
			hoverable
			:embedded
			:disabled
			:clickable="!selectable"
			:loading="canceling"
			@click="selectable ? () => {} : (showDetails = true)"
		>
			<template #headerMain>{{ subscription.name }}</template>
			<template #headerExtra>
				<div class="text-primary">
					{{ price(subscription.price) }}
				</div>
			</template>
			<template v-if="!hideDetails" #default>
				<div class="flex flex-col gap-1">
					{{ subscription.info }}
					<p class="text-sm">
						{{ subscription.short_description }}
					</p>
				</div>
			</template>
			<template v-if="showDeleteOnCard && licenseData" #footerMain>
				<n-popconfirm @positive-click="cancelSubscription()">
					<template #trigger>
						<n-button text size="small">
							<template #icon>
								<Icon :name="DeleteIcon" :size="16" />
							</template>
							Unsubscribe
						</n-button>
					</template>
					{{ deleteMessage }}
				</n-popconfirm>
			</template>
			<template v-if="selectable" #footerExtra>
				<n-button size="small" @click.stop="(showDetails = true)">
					<template #icon>
						<Icon :name="InfoIcon"></Icon>
					</template>
					Details
				</n-button>
			</template>
		</CardEntity>

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
					<div class="text-primary whitespace-nowrap font-mono">
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
import CardEntity from "@/components/common/cards/CardEntity.vue"
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
