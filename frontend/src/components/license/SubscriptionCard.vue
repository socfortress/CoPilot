<template>
	<div class="license-subscription-feature-box" :class="{ embedded, selectable, disabled }">
		<div class="px-4 py-3 flex flex-col gap-2">
			<div class="header-box flex justify-between items-center">
				<div class="flex items-center gap-2 cursor-pointer">
					<span>{{ subscription.name }}</span>
					<span class="info-btn pt-0.5" @click="showDetails = true">
						<Icon :name="InfoIcon" :size="14"></Icon>
					</span>
				</div>
				<div class="price">
					{{ price(subscription.price) }}
				</div>
			</div>
			<div class="main-box flex items-center gap-3" v-if="!hideDetails">
				<div class="content flex flex-col gap-1 grow">
					<div class="title">{{ subscription.info }}</div>
					<div class="description">
						{{ subscription.short_description }}
					</div>
				</div>
			</div>
		</div>

		<n-modal
			v-model:show="showDetails"
			preset="card"
			:style="{ maxWidth: 'min(600px, 90vw)', minHeight: 'min(300px, 90vh)', overflow: 'hidden' }"
			:title="subscription.name"
			:bordered="false"
			content-class="flex flex-col gap-4"
			segmented
		>
			<div class="flex gap-4 justify-between">
				<div>{{ subscription.info }}</div>
				<div class="font-mono whitespace-nowrap text-primary-color">
					{{ price(subscription.price) }}
				</div>
			</div>
			<div>{{ subscription.full_description }}</div>
		</n-modal>
	</div>
</template>

<script setup lang="ts">
import Icon from "@/components/common/Icon.vue"
import { ref, toRefs } from "vue"
import { NModal } from "naive-ui"
import type { SubscriptionFeature } from "@/types/license"
import { price } from "@/utils"

const props = defineProps<{
	subscription: SubscriptionFeature
	embedded?: boolean
	selectable?: boolean
	disabled?: boolean
	hideDetails?: boolean
}>()
const { subscription, embedded, selectable, disabled, hideDetails } = toRefs(props)

const InfoIcon = "carbon:information"
const showDetails = ref(false)
</script>

<style lang="scss" scoped>
.license-subscription-feature-box {
	border-radius: var(--border-radius);
	background-color: var(--bg-color);
	border: var(--border-small-050);
	transition: all 0.2s var(--bezier-ease);

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

	&.selectable {
		cursor: pointer;
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
