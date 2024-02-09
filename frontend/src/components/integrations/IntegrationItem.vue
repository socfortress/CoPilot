<template>
	<div class="integration-item" :class="{ embedded, selectable, disabled }">
		<div class="px-4 py-3 flex flex-col gap-2">
			<div class="header-box flex justify-between items-center">
				<div class="flex items-center gap-2 cursor-pointer">
					<div class="check-box mr-2" v-if="selectable">
						<n-radio size="large" v-model:checked="checked" />
					</div>
					<div class="id">#{{ integration.id }}</div>
				</div>
				<div class="actions">
					<Badge type="cursor" @click.stop="showDetails = true">
						<template #iconLeft>
							<Icon :name="DetailsIcon" :size="14"></Icon>
						</template>
						<template #value>Details</template>
					</Badge>
				</div>
			</div>
			<div class="main-box flex items-center gap-3">
				<div class="content flex flex-col gap-1 grow">
					<div class="title">{{ integration.integration_name }}</div>
					<div class="description">
						{{ integration.description }}
					</div>
				</div>
			</div>

			<div class="badges-box flex flex-wrap items-center gap-3 mt-2">
				<code class="py-1">Auth Keys:</code>
				<Badge v-for="authKey of integration.auth_keys" :key="authKey.auth_key_name">
					<template #value>{{ authKey.auth_key_name }}</template>
				</Badge>
			</div>
		</div>

		<n-modal
			v-model:show="showDetails"
			preset="card"
			:style="{ maxWidth: 'min(800px, 90vw)', minHeight: 'min(400px, 90vh)', overflow: 'hidden' }"
			:title="integration.integration_name"
			:bordered="false"
			segmented
		>
			<Markdown :source="integration.integration_details" />
		</n-modal>
	</div>
</template>

<script setup lang="ts">
import Icon from "@/components/common/Icon.vue"
import Badge from "@/components/common/Badge.vue"
import { defineAsyncComponent, ref, toRefs } from "vue"
import { NModal, NRadio } from "naive-ui"
import type { AvailableIntegration } from "@/types/integrations"
const Markdown = defineAsyncComponent(() => import("@/components/common/Markdown.vue"))

const props = defineProps<{
	integration: AvailableIntegration
	embedded?: boolean
	checked?: boolean
	selectable?: boolean
	disabled?: boolean
}>()
const { integration, embedded, checked, selectable, disabled } = toRefs(props)

const DetailsIcon = "carbon:settings-adjust"

const showDetails = ref(false)
</script>

<style lang="scss" scoped>
.integration-item {
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
