<template>
	<div class="service-item" :class="{ embedded, selectable, disabled }">
		<div class="px-4 py-3 flex flex-col gap-2">
			<div class="header-box flex justify-between items-center">
				<div class="flex items-center gap-2 cursor-pointer">
					<div class="check-box mr-2" v-if="selectable">
						<n-radio size="large" v-model:checked="checked" />
					</div>
					<div class="id">#{{ data.id }}</div>
				</div>
				<div class="actions">
					<n-button size="small" @click.stop="showDetails = true">
						<template #icon>
							<Icon :name="InfoIcon"></Icon>
						</template>
					</n-button>
				</div>
			</div>
			<div class="main-box flex items-center gap-3">
				<div class="content flex flex-col gap-1 grow">
					<div class="title">{{ data.name }}</div>
					<div class="description">
						{{ data.description }}
					</div>
				</div>
			</div>

			<div class="badges-box flex flex-wrap items-center gap-3 mt-2">
				<code class="py-1">Auth Keys:</code>
				<Badge v-for="authKey of data.keys" :key="authKey.auth_key_name">
					<template #value>{{ authKey.auth_key_name }}</template>
				</Badge>
			</div>
		</div>

		<n-modal
			v-model:show="showDetails"
			preset="card"
			:style="{ maxWidth: 'min(800px, 90vw)', minHeight: 'min(400px, 90vh)', overflow: 'hidden' }"
			:title="data.name"
			:bordered="false"
			segmented
		>
			<Suspense>
				<Markdown :source="data.details" />
			</Suspense>
		</n-modal>
	</div>
</template>

<script setup lang="ts">
import { defineAsyncComponent, ref, toRefs } from "vue"
import { NModal, NRadio, NButton } from "naive-ui"
import Icon from "@/components/common/Icon.vue"
import Badge from "@/components/common/Badge.vue"
import type { ServiceItemData, ServiceItemType } from "./types"
const Markdown = defineAsyncComponent(() => import("@/components/common/Markdown.vue"))

const props = defineProps<{
	data: ServiceItemData
	type: ServiceItemType
	embedded?: boolean
	checked?: boolean
	selectable?: boolean
	disabled?: boolean
}>()
const { data, embedded, checked, selectable, disabled } = toRefs(props)

const InfoIcon = "carbon:information"

const showDetails = ref(false)
</script>

<style lang="scss" scoped>
.service-item {
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
