<template>
	<div class="license-subscription-feature-box" :class="{ embedded }">
		<div class="px-4 py-3 flex flex-col gap-2">
			<div class="header-box flex justify-between items-center">
				<div class="flex items-center gap-2 cursor-pointer">
					{{ subscription.name }}
				</div>
				<div class="actions">
					<n-button size="small" @click.stop="showDetails = true">
						<template #icon>
							<Icon :name="InfoIcon"></Icon>
						</template>
						{{ subscription.price }}
					</n-button>
				</div>
			</div>
			<div class="main-box flex items-center gap-3">
				<div class="content flex flex-col gap-1 grow">
					<div class="title">{{ subscription.name }}</div>
					<div class="description">
						{{ subscription.full_description }}
					</div>
				</div>
			</div>
		</div>
	</div>
</template>

<script setup lang="ts">
import Icon from "@/components/common/Icon.vue"
import { ref, toRefs } from "vue"
import { NButton } from "naive-ui"
import type { SubscriptionFeature } from "@/types/license"

const props = defineProps<{
	subscription: SubscriptionFeature
	embedded?: boolean
}>()
const { subscription, embedded } = toRefs(props)

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
		.id {
			font-family: var(--font-family-mono);
			word-break: break-word;
			color: var(--fg-secondary-color);
			line-height: 1.2;
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
